"""
AskTheContract — FastAPI Backend
=================================
Serves the PWA frontend and provides API endpoints for:
  - Authentication (login/register via Turso)
  - Contract search (embeddings + BM25 + context packs + cache)
  - Feedback (ratings + comments via Turso)

All search logic extracted from streamlit_app.py with Streamlit dependencies removed.
Reuses existing modules: auth_manager, contract_manager, contract_logger, cache_manager.
"""

import os
import sys
import types
import time
import re
import math
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# ─────────────────────────────────────────────
# MOCK STREAMLIT — so cache_manager.py imports cleanly
# ─────────────────────────────────────────────
if 'streamlit' not in sys.modules:
    _st = types.ModuleType('streamlit')
    _st.cache_resource = lambda f=None, **kw: f if f else (lambda fn: fn)
    _st.cache_data = lambda f=None, **kw: f if f else (lambda fn: fn)
    sys.modules['streamlit'] = _st

# Add app directory to path so we can import existing modules
APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

# ─── Existing modules (no Streamlit dependency) ───
from auth_manager import register_user, authenticate_user, init_auth_tables
from contract_manager import ContractManager
from contract_logger import ContractLogger
from cache_manager import SemanticCache
from nac_contract_data import *

# ─── API Clients ───
from openai import OpenAI
from anthropic import Anthropic


# ============================================================
# GLOBALS — initialized once at startup
# ============================================================
openai_client: OpenAI = None
anthropic_client: Anthropic = None
contract_manager: ContractManager = None
logger: ContractLogger = None
semantic_cache: SemanticCache = None

# BM25 index cache (replaces @st.cache_data)
_bm25_cache = {}


def init_globals():
    """Initialize all shared resources."""
    global openai_client, anthropic_client, contract_manager, logger, semantic_cache

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not openai_key or not anthropic_key:
        print("[API] WARNING: Missing API keys. Set OPENAI_API_KEY and ANTHROPIC_API_KEY.")

    openai_client = OpenAI(api_key=openai_key) if openai_key else None
    anthropic_client = Anthropic(api_key=anthropic_key) if anthropic_key else None
    contract_manager = ContractManager()
    logger = ContractLogger()
    semantic_cache = SemanticCache()

    init_auth_tables()
    print("[API] ✅ All systems initialized")


# ============================================================
# LIFESPAN — startup/shutdown
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_globals()
    yield


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="AskTheContract API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = ""

class SearchRequest(BaseModel):
    query: str
    contract_id: str = "nac_jcba"

class FeedbackRequest(BaseModel):
    question: str
    rating: str  # "up" or "down"
    contract_id: str = "nac_jcba"
    comment: Optional[str] = ""

class Citation(BaseModel):
    section: str
    page: str
    text: str

class SearchResponse(BaseModel):
    answer: str
    status: str
    citations: List[Citation]
    response_time: float
    cached: bool
    model_tier: Optional[str] = None


# ============================================================
# AUTH ENDPOINTS
# ============================================================
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    result = authenticate_user(req.email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return {
        "success": True,
        "user_id": result["user_id"],
        "display_name": result["display_name"],
        "message": result["message"],
    }


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    result = register_user(req.email, req.password, req.display_name or "")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    # Auto-login after registration
    login_result = authenticate_user(req.email, req.password)
    return {
        "success": True,
        "user_id": login_result.get("user_id", result.get("user_id")),
        "display_name": login_result.get("display_name", req.email.split("@")[0]),
        "message": result["message"],
    }


# ============================================================
# CONTRACTS ENDPOINT
# ============================================================
@app.get("/api/contracts")
async def get_contracts():
    available = contract_manager.get_available_contracts()
    return {
        "contracts": [
            {
                "id": cid,
                "airline_name": info["airline_name"],
                "contract_name": info.get("contract_version", "JCBA"),
            }
            for cid, info in available.items()
        ]
    }


# ============================================================
# SEARCH ENDPOINT
# ============================================================
@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    if not openai_client or not anthropic_client:
        raise HTTPException(status_code=503, detail="API keys not configured")

    start_time = time.time()

    try:
        chunks, embeddings = contract_manager.load_contract_data(req.contract_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contract not found: {e}")

    # Get airline name from contract metadata
    info = contract_manager.get_contract_info(req.contract_id)
    airline_name = info.get("airline_name", "Northern Air Cargo") if info else "Northern Air Cargo"

    # Run the full search pipeline
    answer, status, response_time, cached, model_tier = full_search_pipeline(
        req.query, chunks, embeddings, req.contract_id, airline_name
    )

    # Log the question
    try:
        category = classify_question(req.query)
        logger.log_question(
            question_text=req.query,
            answer_text=answer,
            status=status,
            contract_id=req.contract_id,
            response_time=response_time,
            category=category,
        )
    except Exception as e:
        print(f"[API] Logging failed: {e}")

    # Parse raw answer into structured response
    citations = parse_citations(answer)
    clean_answer = extract_explanation(answer)

    return SearchResponse(
        answer=clean_answer,
        status=status,
        citations=citations,
        response_time=round(time.time() - start_time, 2),
        cached=cached,
        model_tier=model_tier,
    )


# ============================================================
# FEEDBACK ENDPOINT
# ============================================================
@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    try:
        logger.log_rating(req.question, req.rating, req.contract_id, req.comment or "")
        if req.rating == "down":
            try:
                semantic_cache.record_thumbs_down(req.question, req.contract_id)
            except Exception:
                pass
            if req.comment:
                try:
                    semantic_cache.save_feedback(req.question, req.contract_id, req.comment)
                except Exception:
                    pass
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# STATIC FILE SERVING (PWA)
# ============================================================
PWA_DIR = APP_DIR / "pwa"

@app.get("/")
async def serve_index():
    index_path = PWA_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "AskTheContract API is running. PWA files not found in /pwa directory."}

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(PWA_DIR / "manifest.json", media_type="application/json")

@app.get("/service-worker.js")
async def serve_sw():
    return FileResponse(PWA_DIR / "service-worker.js", media_type="application/javascript")

# Mount icons directory
if (PWA_DIR / "icons").exists():
    app.mount("/icons", StaticFiles(directory=str(PWA_DIR / "icons")), name="icons")


# ============================================================
# ============================================================
#
#   SEARCH ENGINE — extracted from streamlit_app.py
#   No Streamlit dependencies. Pure Python.
#
# ============================================================
# ============================================================


# ── Question Categories (keyword matching, no AI) ──
QUESTION_CATEGORIES = {
    "Pay → Hourly Rate": ['hourly rate', 'pay rate', 'what do i make', 'how much do i make', 'rate of pay', 'longevity rate', 'current rate'],
    "Pay → Daily Pay Guarantee": ['dpg', 'daily pay guarantee', 'minimum pay per day', 'daily guarantee'],
    "Pay → Duty Rig": ['duty rig', 'duty day pay', '1:2'],
    "Pay → Trip Rig / TAFD": ['trip rig', 'tafd', 'time away from domicile'],
    "Pay → Overtime / Premium": ['overtime', 'open time premium', 'premium pay', 'time and a half'],
    "Pay → Junior Assignment Premium": ['junior assignment premium', 'ja premium', 'ja pay'],
    "Pay → General Calculation": ['pay', 'paid', 'compensation', 'wage', 'salary', 'earning', 'pch'],
    "Reserve → Types & Definitions": ['reserve type', 'reserve duty', 'reserve rules', 'reserve', 'r-1', 'r-2', 'r-3', 'r-4', 'what is reserve'],
    "Reserve → FIFO": ['fifo', 'first in first out', 'reserve order'],
    "Reserve → Availability / RAP": ['reserve availability', 'rap', 'on call', 'call out'],
    "Reserve → Day-Off Reassignment": ['reserve day off', 'called on day off', 'junior assigned', 'involuntary assign'],
    "Scheduling → Days Off": ['day off', 'days off', 'time off', 'week off', 'off per week', 'off a week', 'days a week'],
    "Scheduling → Rest Periods": ['rest period', 'rest requirement', 'minimum rest', 'duty free'],
    "Scheduling → Line Construction": ['line construction', 'bid line', 'regular line', 'composite line', 'reserve line', 'domicile flex'],
    "Scheduling → Reassignment": ['reassign', 'reassignment', 'schedule change'],
    "Scheduling → Duty Limits": ['duty limit', 'duty time', 'max duty', 'maximum duty'],
    "Training": ['training', 'upgrade', 'transition', 'simulator', 'check ride', 'recurrent'],
    "Seniority": ['seniority', 'seniority list', 'seniority number', 'bid order'],
    "Grievance": ['grievance', 'grieve', 'dispute', 'arbitration', 'system board'],
    "TDY": ['tdy', 'temporary duty', 'tdy line'],
    "Vacation / Leave": ['vacation', 'leave', 'sick leave', 'bereavement', 'military leave', 'fmla'],
    "Benefits": ['insurance', 'health', 'medical', 'dental', 'retirement', '401k'],
    "Furlough": ['furlough', 'recall', 'laid off', 'reduction'],
    "Expenses / Per Diem": ['per diem', 'meal allowance', 'meal money', 'hotel', 'lodging', 'expenses', 'transportation', 'parking'],
    "Sick Leave": ['sick', 'sick call', 'sick leave', 'calling in sick', 'illness', 'sick pay', 'sick bank'],
    "Deadhead": ['deadhead', 'deadhead pay', 'deadhead rest', 'positioning', 'repositioning'],
    "Hours of Service": ['hours of service', 'flight time limit', 'block limit', 'rest interruption', 'rest interrupted'],
}


def classify_question(question_text):
    q_lower = question_text.lower()
    best_match = None
    best_count = 0
    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > best_count:
            best_count = count
            best_match = category
    return best_match if best_match else "General Contract Question"


# ── Question Preprocessor ──
_SHORTHAND_MAP = [
    (r"\bwhats\b", "what is"), (r"\bwhat's\b", "what is"), (r"\bhow's\b", "how is"),
    (r"\bcan't\b", "cannot"), (r"\bdon't\b", "do not"), (r"\bdoesn't\b", "does not"),
    (r"\bwon't\b", "will not"), (r"\bdidn't\b", "did not"), (r"\bwasn't\b", "was not"),
    (r"\bi'm\b", "i am"), (r"\bi've\b", "i have"), (r"\bi'd\b", "i would"),
    (r"\bca\b", "captain"), (r"\bcapt\b", "captain"),
    (r"\bfo\b", "first officer"), (r"\bf/o\b", "first officer"),
    (r"\bpic\b", "pilot in command"), (r"\bsic\b", "second in command"),
    (r"\br1\b", "r-1"), (r"\br2\b", "r-2"), (r"\br3\b", "r-3"), (r"\br4\b", "r-4"),
    (r"\bja'd\b", "junior assigned"), (r"\bja'ed\b", "junior assigned"),
    (r"\bjaed\b", "junior assigned"), (r"\bja\b", "junior assignment"),
    (r"\bext'd\b", "extended"), (r"\bexted\b", "extended"),
    (r"\bdeadhd\b", "deadhead"), (r"\bdh\b", "deadhead"), (r"\bd/h\b", "deadhead"),
    (r"\bmx\b", "mechanical"), (r"\bmech\b", "mechanical"),
    (r"\bpax\b", "passenger"), (r"\bsked\b", "schedule"), (r"\bskd\b", "schedule"),
    (r"\bdom\b", "domicile"), (r"\bvac\b", "vacation"),
    (r"\byr\b", "year"), (r"\byrs\b", "years"), (r"\bhr\b", "hour"), (r"\bhrs\b", "hours"),
    (r"\bOT\b", "overtime"), (r"\bot\b", "overtime"),
    (r"\bsect\b", "section"), (r"\bsec\b", "section"),
    (r"\bjcba\b", "contract"), (r"\bcba\b", "contract"),
    (r"\b73\b", "b737"), (r"\b737\b", "b737"),
    (r"\bslb\b", "sick leave bank"), (r"\birop\b", "irregular operations"),
    (r"\bsap\b", "schedule adjustment period"), (r"\bmpg\b", "monthly pay guarantee"),
    (r"\balpa\b", "union"), (r"\bioe\b", "initial operating experience"),
    (r"\bldt\b", "local domicile time"),
]
_SHORTHAND_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _SHORTHAND_MAP]


def preprocess_question(question_text):
    result = question_text
    for pattern, replacement in _SHORTHAND_COMPILED:
        result = pattern.sub(replacement, result)
    return re.sub(r'  +', ' ', result).strip()


# ── Cosine Similarity ──
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ── BM25 Keyword Search ──
_BM25_STOPWORDS = frozenset([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'between',
    'through', 'after', 'before', 'during', 'and', 'or', 'but', 'not',
    'no', 'nor', 'if', 'then', 'than', 'that', 'this', 'these', 'those',
    'it', 'its', 'he', 'his', 'him', 'i', 'my', 'me', 'we', 'our',
    'you', 'your', 'they', 'their', 'what', 'which', 'who', 'when',
    'where', 'how', 'all', 'each', 'any', 'both', 'such', 'other',
])


def _bm25_tokenize(text):
    tokens = re.findall(r'[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?', text.lower())
    return [t for t in tokens if t not in _BM25_STOPWORDS and len(t) > 1]


def _build_bm25_index(chunk_texts):
    """Build BM25 index — cached by chunk_texts hash."""
    cache_key = hashlib.md5(str(chunk_texts[:5]).encode()).hexdigest()
    if cache_key in _bm25_cache:
        return _bm25_cache[cache_key]

    doc_tokens = [_bm25_tokenize(text) for text in chunk_texts]
    doc_count = len(doc_tokens)
    avg_dl = sum(len(d) for d in doc_tokens) / doc_count if doc_count > 0 else 1
    df = {}
    for tokens in doc_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1)

    result = (doc_tokens, idf, avg_dl)
    _bm25_cache[cache_key] = result
    return result


def _bm25_search(query, chunks, top_n=15, k1=1.5, b=0.75):
    chunk_texts = tuple(c['text'] for c in chunks)
    doc_tokens, idf, avg_dl = _build_bm25_index(chunk_texts)
    query_tokens = _bm25_tokenize(query)
    if not query_tokens:
        return []
    scores = []
    for i, tokens in enumerate(doc_tokens):
        dl = len(tokens)
        score = 0.0
        tf_map = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        for qt in query_tokens:
            if qt in tf_map:
                tf = tf_map[qt]
                term_idf = idf.get(qt, 0)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / avg_dl)
                score += term_idf * numerator / denominator
        if score > 0:
            scores.append((score, chunks[i]))
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_n]


# ── Embedding (with in-memory cache) ──
_embedding_cache = {}


def get_embedding(text):
    if text in _embedding_cache:
        return _embedding_cache[text]
    response = openai_client.embeddings.create(input=text, model="text-embedding-3-small")
    emb = response.data[0].embedding
    _embedding_cache[text] = emb
    return emb


# ── Force Include Chunks ──
def find_force_include_chunks(question_lower, all_chunks):
    forced = []
    for rule_name, rule in FORCE_INCLUDE_RULES.items():
        if any(kw in question_lower for kw in rule['trigger_keywords']):
            for chunk in all_chunks:
                chunk_text_lower = ' '.join(chunk['text'].lower().split())
                for phrase in rule['must_include_phrases']:
                    if phrase in chunk_text_lower:
                        if chunk not in forced:
                            forced.append(chunk)
                        break
    return forced


# ── Context Packs ──
def get_pack_chunks(pack_key, all_chunks):
    if pack_key not in CONTEXT_PACKS:
        return []
    pages = set(CONTEXT_PACKS[pack_key]['pages'])
    return [c for c in all_chunks if c['page'] in pages]


def classify_all_matching_packs(question_text):
    q_lower = question_text.lower()
    pack_scores = {}
    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > 0:
            pack_key = CATEGORY_TO_PACK.get(category)
            if pack_key and pack_key in CONTEXT_PACKS:
                pack_scores[pack_key] = max(pack_scores.get(pack_key, 0), count)
    sorted_packs = sorted(pack_scores.items(), key=lambda x: x[1], reverse=True)
    return [pk for pk, _ in sorted_packs]


# ── Search Contract (merge all sources) ──
def search_contract(question, chunks, embeddings, max_chunks=75):
    question_embedding = get_embedding(question)
    question_lower = question.lower()
    forced_chunks = find_force_include_chunks(question_lower, chunks)

    matching_packs = classify_all_matching_packs(question)

    if matching_packs:
        merged_pages = set()
        for pk in matching_packs:
            merged_pages.update(CONTEXT_PACKS[pk]['pages'])
        for keyword, chain_pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                merged_pages.update(chain_pages)
        pack_chunks = [c for c in chunks if c['page'] in merged_pages]
        if len(matching_packs) > 1:
            max_total = 35
            embedding_top_n = 10
        else:
            max_total = CONTEXT_PACKS[matching_packs[0]].get('max_total', 30)
            embedding_top_n = CONTEXT_PACKS[matching_packs[0]].get('embedding_top_n', 15)
        max_pack = max_total - min(embedding_top_n, 5)
        if len(pack_chunks) > max_pack:
            id_to_idx = {c.get('id'): i for i, c in enumerate(chunks)}
            pack_scores = []
            for pc in pack_chunks:
                idx = id_to_idx.get(pc.get('id'))
                score = cosine_similarity(question_embedding, embeddings[idx]) if idx is not None else 0
                pack_scores.append((score, pc))
            pack_scores.sort(reverse=True, key=lambda x: x[0])
            pack_chunks = [pc for _, pc in pack_scores[:max_pack]]
    else:
        chain_pages = set()
        for keyword, pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                chain_pages.update(pages)
        pack_chunks = [c for c in chunks if c['page'] in chain_pages] if chain_pages else []
        embedding_top_n = 30
        max_total = 30

    # Embedding search
    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))
    similarities.sort(reverse=True, key=lambda x: x[0])
    embedding_chunks = [chunk for score, chunk in similarities[:embedding_top_n]]

    # BM25
    bm25_top_n = min(10, embedding_top_n)
    bm25_results = _bm25_search(question, chunks, top_n=bm25_top_n)
    bm25_chunks = [chunk for score, chunk in bm25_results]

    # Merge: forced → pack → BM25 → embedding (deduplicated)
    seen_ids = set()
    merged = []
    for source in [forced_chunks, pack_chunks, bm25_chunks, embedding_chunks]:
        for chunk in source:
            chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(chunk)
                if len(merged) >= max_total:
                    break
        if len(merged) >= max_total:
            break

    return merged


# ── Pay Calculator ──
def _build_pay_reference(question):
    q = question.lower()
    pay_triggers = ['pay', 'paid', 'compensation', 'make', 'earn', 'rate', 'rig',
                    'dpg', 'premium', 'overtime', 'pch', 'wage', 'salary',
                    'junior assignment', 'ja ', 'open time', 'day off']
    if not any(t in q for t in pay_triggers):
        return ""

    if 'captain' in q or 'capt ' in q:
        positions = ['Captain']
    elif 'first officer' in q or 'fo ' in q or 'f/o' in q:
        positions = ['First Officer']
    else:
        positions = ['Captain', 'First Officer']

    year_match = re.search(r'year\s*(\d{1,2})', q)
    if not year_match:
        year_match = re.search(r'(\d{1,2})[\s-]*year', q)
    year = int(year_match.group(1)) if year_match and 1 <= int(year_match.group(1)) <= 12 else None

    duty_hours = block_hours = tafd_hours = None
    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hours = float(duty_match.group(1))
    block_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:block|flight|flying|flew)', q)
    if not block_match:
        block_match = re.search(r'(?:block|flight|flew)\s*(?:time)?\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if block_match:
        block_hours = float(block_match.group(1))
    tafd_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:tafd|away from domicile|time away)', q)
    if not tafd_match:
        tafd_match = re.search(r'(?:tafd|time away|away from domicile)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if tafd_match:
        tafd_hours = float(tafd_match.group(1))

    premiums = {}
    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        premiums['Junior Assignment 1st in 3mo (200%)'] = 2.00
        premiums['Junior Assignment 2nd in 3mo (250%)'] = 2.50

    has_scenario = duty_hours or block_hours or tafd_hours
    lines = ["PRE-COMPUTED PAY REFERENCE (use these exact numbers — do not recalculate):"]
    lines.append(f"Current pay multiplier: DOS rate x 1.02^{PAY_INCREASES} = DOS x {PAY_MULTIPLIER:.5f}")
    lines.append("")

    years_to_show = [year] if year else list(range(1, 13))
    for pos in positions:
        for y in years_to_show:
            dos = PAY_RATES_DOS['B737'][pos][y]
            current = round(dos * PAY_MULTIPLIER, 2)
            lines.append(f"B737 {pos} Year {y}: DOS {dos:.2f} → Current {current:.2f}/hour")

    if has_scenario and year:
        lines.append("")
        lines.append("PAY CALCULATIONS FOR THIS SCENARIO:")
        for pos in positions:
            dos = PAY_RATES_DOS['B737'][pos][year]
            rate = round(dos * PAY_MULTIPLIER, 2)
            lines.append(f"  {pos} Year {year} rate: {rate:.2f}/hour")
            calcs = []
            if block_hours is not None:
                val = round(block_hours * rate, 2)
                calcs.append(f"    Block Time: {block_hours} PCH x {rate:.2f} = {val:.2f}")
            dpg_val = round(3.82 * rate, 2)
            calcs.append(f"    DPG (minimum): 3.82 PCH x {rate:.2f} = {dpg_val:.2f}")
            if duty_hours is not None:
                rig_pch = round(duty_hours / 2, 2)
                rig_val = round(rig_pch * rate, 2)
                calcs.append(f"    Duty Rig: {duty_hours} hrs / 2 = {rig_pch} PCH x {rate:.2f} = {rig_val:.2f}")
            if tafd_hours is not None:
                trip_pch = round(tafd_hours / 4.9, 2)
                trip_val = round(trip_pch * rate, 2)
                calcs.append(f"    Trip Rig: {tafd_hours} hrs / 4.9 = {trip_pch} PCH x {rate:.2f} = {trip_val:.2f}")
            pch_values = {'DPG': 3.82}
            if block_hours is not None:
                pch_values['Block Time'] = block_hours
            if duty_hours is not None:
                pch_values['Duty Rig'] = round(duty_hours / 2, 2)
            if tafd_hours is not None:
                pch_values['Trip Rig'] = round(tafd_hours / 4.9, 2)
            best_name = max(pch_values, key=pch_values.get)
            best_pch = pch_values[best_name]
            best_pay = round(best_pch * rate, 2)
            for c in calcs:
                lines.append(c)
            lines.append(f"    → GREATEST: {best_name} = {best_pch} PCH = {best_pay:.2f} at 100%")
            if premiums:
                lines.append("")
                lines.append("    WITH PREMIUMS:")
                for prem_name, mult in premiums.items():
                    prem_pay = round(best_pch * rate * mult, 2)
                    lines.append(f"    {prem_name}: {best_pch} PCH x {rate:.2f} x {mult} = {prem_pay:.2f}")
            lines.append("")

    return "\n".join(lines)


# ── Grievance Pattern Detector ──
def _detect_grievance_patterns(question):
    q = question.lower()
    alerts = []

    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hrs = float(duty_match.group(1))
        if duty_hrs > 16:
            alerts.append(f"⚠️ DUTY TIME ALERT: {duty_hrs} hours exceeds the 16-hour maximum for a basic 2-pilot crew (Section 13.F.1).")
        elif duty_hrs > 14:
            alerts.append(f"⚠️ REST REQUIREMENT ALERT: {duty_hrs} hours of duty triggers the 12-hour minimum rest requirement (Section 13.G.1).")

    rest_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:rest|off|between)', q)
    if rest_match:
        rest_hrs = float(rest_match.group(1))
        if rest_hrs < 10:
            alerts.append(f"⚠️ REST VIOLATION ALERT: {rest_hrs} hours of rest is below the 10-hour minimum (Section 13.G.1).")

    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        alerts.append("⚠️ JA CHECKLIST: Verify inverse seniority, 1st vs 2nd JA in 3-month period, extension limits.")
    if 'extend' in q or 'extension' in q:
        alerts.append("⚠️ EXTENSION CHECKLIST: Per Section 14.N — only ONE involuntary extension per month.")
    if 'schedule change' in q or 'reassign' in q or 'text message' in q or 'text only' in q or 'email only' in q:
        alerts.append("⚠️ POSITIVE CONTACT REQUIRED: Per MOU #2 (Page 381), schedule changes require verbal acknowledgment.")

    if not alerts:
        return ""
    return "GRIEVANCE PATTERN ALERTS:\n" + "\n".join(alerts)


# ── Model Routing ──
MODEL_TIERS = {
    'simple': 'claude-haiku-4-5-20251001',
    'standard': 'claude-sonnet-4-20250514',
    'complex': 'claude-opus-4-20250514',
}

_COMPLEX_INDICATORS = [
    'what do i get paid', 'what would i get paid', 'what should i get paid',
    'what am i owed', 'how much should i be paid', 'calculate my pay',
    'into my day off', 'into a day off', 'past my day off',
    'extended into', 'crossed into', 'extended and', 'junior assigned and',
    'is this a grievance', 'should i grieve', 'contract violation',
    'difference between', 'compared to', 'which is better',
]

_SIMPLE_PATTERNS = [
    r'^what section (?:covers|talks about|addresses|is about)',
    r'^where (?:can i find|does it talk about|is the section)',
    r'^which section', r'^what page',
    r'^(?:does|is|can|are) (?:the contract|there a)',
    r'^what (?:is|are) (?:a |an |the )?[\w\s]{1,25}\??$',
]
_SIMPLE_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]


def _classify_complexity(question_lower, matching_packs=None, has_pay_ref=False, has_grievance_ref=False):
    scenario_count = 0
    scenario_keywords = ['duty', 'block', 'flew', 'hours', 'day off', 'overtime',
                         'extension', 'junior assign', 'reserve', 'rap']
    for kw in scenario_keywords:
        if kw in question_lower:
            scenario_count += 1
    has_numbers = bool(re.search(r'\d+(?:\.\d+)?\s*(?:hours?|hr|pch|am|pm)', question_lower))
    has_times = bool(re.search(r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|noon|midnight|\d{4}\s*(?:ldt|local|zulu)', question_lower))

    if has_numbers and scenario_count >= 2:
        return 'complex'
    if has_times and any(kw in question_lower for kw in ['pay', 'paid', 'overtime', 'premium', 'owed']):
        return 'complex'
    if any(ind in question_lower for ind in _COMPLEX_INDICATORS):
        return 'complex'
    if has_pay_ref and has_grievance_ref:
        return 'complex'
    if matching_packs and len(matching_packs) >= 2:
        if has_numbers or has_times:
            return 'complex'
        return 'standard'
    if len(question_lower.split()) <= 10:
        for pattern in _SIMPLE_COMPILED:
            if pattern.search(question_lower):
                return 'simple'
    if scenario_count == 0 and not has_numbers and not has_times:
        if not has_pay_ref and not has_grievance_ref:
            if len(question_lower.split()) <= 8:
                return 'simple'
    return 'standard'


# ── Tier 1 Instant Answers ──
def tier1_instant_answer(question_lower):
    """Check for instant answers (no API call). Returns (answer, status, time) or None."""
    start = time.time()

    # Fixed-value rule lookups
    for rule_key, rule in TIER1_RULES.items():
        if any(kw in question_lower for kw in rule['keywords']):
            has_numeric = re.search(r'\d+(?:\.\d+)?\s*hours?\s*(?:of\s+)?(?:duty|rest|block|on duty)', question_lower)
            if not has_numeric:
                return rule['answer'], 'CLEAR', round(time.time() - start, 1)

    # Per diem (dynamic based on date)
    if any(kw in question_lower for kw in PER_DIEM_KEYWORDS):
        now = datetime.now()
        anniversaries = now.year - DOS_DATE.year
        if (now.month, now.day) < (DOS_DATE.month, DOS_DATE.day):
            anniversaries -= 1
        anniversaries = max(0, anniversaries)
        current_domestic = PER_DIEM_BASE_DOMESTIC + anniversaries
        current_international = PER_DIEM_BASE_INTERNATIONAL + anniversaries
        answer = f"""📄 CONTRACT LANGUAGE: "For Duty or other Company-Directed Assignments that are performed within the Contiguous United States, including all time during a layover in the United States, Fifty-Six Dollars ($56) per Day." 📍 Section 6.C.2.a, Page 99

"The Per Diem rates shall be increased by one (1) Dollar ($1.00) per Day on each anniversary date of the Agreement." 📍 Section 6.C.2.c, Page 100

📝 EXPLANATION: Base rates (DOS July 24, 2018): 56/day domestic, 72/day international. After {anniversaries} anniversary increases:
- Domestic: 56 + {anniversaries} = **{current_domestic}/day**
- International: 72 + {anniversaries} = **{current_international}/day**

🔵 STATUS: CLEAR - Per diem rates explicitly stated in Section 6.C.2.

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice."""
        return answer, 'CLEAR', round(time.time() - start, 1)

    # Scenario detection — skip tier1 for complex questions
    scenario_indicators = ['duty', 'block', 'tafd', 'flew', 'flying', 'flight time',
                           'time away', 'junior assign', 'ja ', 'open time pick',
                           'extension', 'reassign', 'day off', 'overtime',
                           'what do i get paid', 'what would i get paid', 'on reserve']
    if any(s in question_lower for s in scenario_indicators):
        return None

    # Pay rate lookups
    pay_keywords = ['pay rate', 'hourly rate', 'make per hour', 'paid per hour',
                    'how much', 'what rate', 'pay scale']
    if any(kw in question_lower for kw in pay_keywords):
        year_match = re.search(r'year\s*(\d{1,2})', question_lower) or re.search(r'(\d{1,2})[\s-]*year', question_lower)
        if year_match:
            year = int(year_match.group(1))
            if 1 <= year <= 12:
                if 'captain' in question_lower or 'capt' in question_lower:
                    position = 'Captain'
                elif 'first officer' in question_lower or 'fo ' in question_lower:
                    position = 'First Officer'
                else:
                    position = None
                combos = [('B737', position)] if position else [('B737', 'Captain'), ('B737', 'First Officer')]
                rate_lines = []
                for ac, pos in combos:
                    dos_rate = PAY_RATES_DOS[ac][pos][year]
                    current_rate = round(dos_rate * PAY_MULTIPLIER, 2)
                    rate_lines.append(f'- {pos} Year {year}: DOS rate {dos_rate:.2f} x 1.02^{PAY_INCREASES} = {current_rate:.2f} per hour')
                answer = f"""📄 CONTRACT LANGUAGE: "B737 pay rates" 📍 Appendix A, Page 66

"Hourly Pay Rates shall increase by two percent (2%) annually." 📍 Section 3.B.3, Page 50

📝 EXPLANATION: B737 Year {year} pay rates after {PAY_INCREASES} annual increases:

{chr(10).join(rate_lines)}

🔵 STATUS: CLEAR - Pay rates in Appendix A with annual increase formula in Section 3.B.3.

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice."""
                return answer, 'CLEAR', round(time.time() - start, 1)

    # Definition lookups
    def_patterns = [
        r'what (?:does|is|are|do)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*(?:mean|stand for|definition)',
        r'define\s+["\']?(.+?)["\']?\s*$',
        r'what (?:is|are)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*\??\s*$',
    ]
    for pattern in def_patterns:
        match = re.search(pattern, question_lower.strip().rstrip('?'))
        if match:
            term = match.group(1).strip().lower()
            term = re.sub(r'\s+(mean|means|stand|stands|defined|definition).*$', '', term)
            if term in DEFINITIONS_LOOKUP:
                display_term = term.upper() if len(term) <= 4 else term.title()
                answer = f"""📄 CONTRACT LANGUAGE: "{display_term}: {DEFINITIONS_LOOKUP[term]}" 📍 Section 2, Pages 13-45

📝 EXPLANATION: Per Section 2, **{display_term}** is defined as: {DEFINITIONS_LOOKUP[term]}

🔵 STATUS: CLEAR - Explicitly defined in Section 2.

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice."""
                return answer, 'CLEAR', round(time.time() - start, 1)

    return None


# ── API Call (Anthropic) ──
def _ask_question_api(question, chunks, embeddings, contract_id, airline_name):
    start_time = time.time()
    relevant_chunks = search_contract(question, chunks, embeddings)

    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")
    context = "\n\n---\n\n".join(context_parts)

    pay_ref = _build_pay_reference(question)
    grievance_ref = _detect_grievance_patterns(question)

    matching_packs = classify_all_matching_packs(question)
    model_tier = _classify_complexity(
        question.lower(), matching_packs=matching_packs,
        has_pay_ref=bool(pay_ref), has_grievance_ref=bool(grievance_ref),
    )
    model_name = MODEL_TIERS[model_tier]
    print(f"[Router] {model_tier.upper()} → {model_name} | Q: {question[:80]}")

    q_lower = question.lower()
    is_pay_question = any(kw in q_lower for kw in [
        'pay', 'paid', 'compensation', 'wage', 'salary', 'rate', 'pch',
        'rig', 'dpg', 'premium', 'overtime', 'owed', 'earn',
        'junior assign', 'ja ', 'open time', 'day off',
        'block', 'duty', 'tafd', 'flew', 'flying', 'hours'
    ])

    if model_tier == 'simple':
        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA).
SCOPE: This tool ONLY searches the {airline_name} JCBA. No FARs, company manuals, or other policies.
RULES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Use neutral language ("the contract states" not "you get")
4. Acknowledge when the contract is silent
STATUS: CLEAR (unambiguous), AMBIGUOUS (multiple interpretations), NOT ADDRESSED (no relevant language)
FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
📝 EXPLANATION: [Plain English]
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice.
FORMATTING: Use **bold** for labels, not markdown headings. No $ signs."""
        max_tokens = 1000
    else:
        pay_sections = ""
        if is_pay_question:
            pay_sections = f"""
CURRENT PAY RATES:
DOS = July 24, 2018. Rates increase 2% annually. {PAY_INCREASES} increases applied. CURRENT = DOS rate × {PAY_MULTIPLIER:.5f}.
PAY QUESTION RULES: Calculate ALL four pay provisions (Block, Duty Rig, DPG 3.82, Trip Rig) and show which is GREATEST.
Do NOT use dollar signs ($)."""

        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA).
SCOPE: ONLY the {airline_name} JCBA. No FARs, company manuals, or other policies.
CORE PRINCIPLES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Use neutral language
4. Acknowledge when the contract is silent
5. Read ALL provided sections before answering
KEY DEFINITIONS: Block Time = brakes released to brakes set. Day Off = calendar day free of ALL Duty at Domicile.
DPG = 3.82 PCH minimum per Day. Duty Rig = 1 PCH per 2 hours Duty. Trip Rig = TAFD ÷ 4.9.
{pay_sections}
STATUS: 🔵 CLEAR / 🔵 AMBIGUOUS / 🔵 NOT ADDRESSED
FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
(Repeat for each provision)
📝 EXPLANATION: [Plain English analysis]
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice.
FORMATTING: Use **bold** for labels, no markdown headings (#). No $ signs. Keep compact."""
        max_tokens = 2000 if model_tier == 'complex' else 1500

    user_content = f"CONTRACT SECTIONS:\n{context}\n\nQUESTION: {question}\n"
    if pay_ref:
        user_content += f"\n{pay_ref}\n"
    if grievance_ref:
        user_content += f"\n{grievance_ref}\n"
    user_content += "\nAnswer:"

    message = anthropic_client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        temperature=0,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
        messages=[{"role": "user", "content": user_content}],
    )

    answer = message.content[0].text
    response_time = time.time() - start_time

    if '🔵 STATUS: CLEAR' in answer:
        status = 'CLEAR'
    elif '🔵 STATUS: AMBIGUOUS' in answer:
        status = 'AMBIGUOUS'
    else:
        status = 'NOT_ADDRESSED'

    return answer, status, response_time, model_tier


# ── Full Search Pipeline ──
def full_search_pipeline(question, chunks, embeddings, contract_id, airline_name):
    """Returns (answer, status, response_time, cached, model_tier)"""
    normalized = preprocess_question(question.strip()).lower()

    # Tier 1: Instant answers
    tier1_result = tier1_instant_answer(normalized)
    if tier1_result is not None:
        answer, status, rt = tier1_result
        return answer, status, rt, False, 'tier1'

    # Cache check
    question_embedding = get_embedding(normalized)
    cached_result = semantic_cache.lookup(question_embedding, contract_id)
    if cached_result is not None:
        cached_answer, cached_status, cached_time = cached_result
        return cached_answer, cached_status, 0.0, True, 'cached'

    # Full API call
    answer, status, response_time, model_tier = _ask_question_api(
        normalized, chunks, embeddings, contract_id, airline_name
    )

    # Cache the result (except NOT_ADDRESSED)
    if status != 'NOT_ADDRESSED':
        category = classify_question(normalized)
        semantic_cache.store(question_embedding, normalized, answer, status, response_time, contract_id, category)

    return answer, status, response_time, False, model_tier


# ============================================================
# ANSWER PARSER — converts raw Claude output to structured JSON
# ============================================================
def parse_citations(raw_answer):
    """Extract citations from raw answer text.
    Looks for patterns like: 📄 CONTRACT LANGUAGE: "..." 📍 Section X.Y, Page N
    """
    citations = []

    # Pattern: 📄 CONTRACT LANGUAGE: "..." 📍 Section/Appendix ..., Page N
    pattern = r'📄\s*CONTRACT LANGUAGE:\s*["\u201c](.+?)["\u201d]\s*📍\s*(.+?)(?:\n|$)'
    matches = re.findall(pattern, raw_answer, re.DOTALL)

    for quote_text, location in matches:
        quote_text = quote_text.strip()
        location = location.strip()

        # Parse location into section and page
        page_match = re.search(r'Page\s*(\d+)', location)
        page = f"Page {page_match.group(1)}" if page_match else ""

        # Section is everything before the page reference
        section = re.sub(r',?\s*Page\s*\d+.*$', '', location).strip()
        if not section:
            section = location

        citations.append(Citation(section=section, page=page, text=quote_text))

    # Also try CITE: format from older cached answers
    cite_pattern = r'CITE:\s*(.+?)(?:\n|$)'
    cite_matches = re.findall(cite_pattern, raw_answer)
    for cite in cite_matches:
        if not any(c.text[:30] in cite for c in citations):
            citations.append(Citation(section=cite.strip(), page="", text=""))

    return citations


def extract_explanation(raw_answer):
    """Extract the explanation/analysis portion from raw answer."""
    # Try to find the 📝 EXPLANATION section
    expl_match = re.search(r'📝\s*EXPLANATION:\s*(.+?)(?=🔵\s*STATUS:|⚠️|$)', raw_answer, re.DOTALL)
    if expl_match:
        explanation = expl_match.group(1).strip()
        # Also append the status line
        status_match = re.search(r'🔵\s*STATUS:\s*(.+?)(?=⚠️|$)', raw_answer, re.DOTALL)
        if status_match:
            explanation += "\n\n🔵 STATUS: " + status_match.group(1).strip()
        return explanation

    # If no structured format found, return the full answer minus disclaimer
    answer = re.sub(r'⚠️\s*Disclaimer:.*$', '', raw_answer, flags=re.DOTALL).strip()
    return answer


# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/api/health")
async def health():
    cache_stats = semantic_cache.stats() if semantic_cache else {}
    return {
        "status": "ok",
        "openai": openai_client is not None,
        "anthropic": anthropic_client is not None,
        "contracts": len(contract_manager.get_available_contracts()) if contract_manager else 0,
        "cache": cache_stats,
    }


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
