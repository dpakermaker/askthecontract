import streamlit as st
import pickle
import numpy as np
from openai import OpenAI
from anthropic import Anthropic
import time
import sys
import threading
import json
import os
from pathlib import Path
from datetime import datetime
import re
import math

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from contract_manager import ContractManager
from contract_logger import ContractLogger
from nac_contract_data import *

# Page config
st.set_page_config(
    page_title="AskTheContract",
    page_icon="✈️",
    layout="wide"
)

# ============================================================
# PROFESSIONAL CSS THEME
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Global typography ── */
    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ── Page background ── */
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Hide page navigation in sidebar ── */
    [data-testid="stSidebarNav"] { display: none; }

    .block-container {
        padding-top: 1.5rem !important;
        max-width: 900px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0f172a;
        border-right: none;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #334155;
    }
    [data-testid="stSidebar"] .stSelectbox label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #94a3b8 !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: #1e293b;
        color: #e2e8f0;
        border: 1px solid #334155;
        border-radius: 8px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 0.85rem;
        transition: all 0.15s ease;
        text-align: left;
        padding: 0.5rem 0.75rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #334155;
        border-color: #475569;
        color: #ffffff;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background: #1e293b;
        border: 1px solid #334155;
        color: #cbd5e1;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stSubheader {
        color: #94a3b8 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    /* ── Main content inputs ── */
    .stTextInput > div > div > input {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.95rem;
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem 1rem;
        transition: border-color 0.15s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    .stTextInput label {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        color: #334155;
        font-size: 0.9rem;
    }

    /* ── Primary button ── */
    .stFormSubmitButton > button,
    button[kind="primary"] {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-size: 0.9rem;
        letter-spacing: 0.01em;
    }

    /* ── Answer boxes ── */
    [data-testid="stAlert"] {
        border-radius: 10px;
        font-family: 'DM Sans', sans-serif;
        line-height: 1.65;
        font-size: 0.9rem;
        border-left-width: 4px;
    }
    /* Cap heading sizes inside answers — safety net */
    [data-testid="stAlert"] h1 {
        font-size: 1rem !important;
        font-weight: 700 !important;
        margin: 0.75rem 0 0.35rem !important;
    }
    [data-testid="stAlert"] h2 {
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        margin: 0.6rem 0 0.3rem !important;
    }
    [data-testid="stAlert"] h3 {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        margin: 0.5rem 0 0.25rem !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 0.85rem;
        color: #64748b;
    }

    /* ── General buttons ── */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        border-radius: 8px;
    }

    /* ── Markdown headings ── */
    .stMarkdown h3 {
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        color: #0f172a;
        font-size: 1.05rem;
        letter-spacing: -0.01em;
    }

    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        font-family: 'DM Sans', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FEATURE 1: QUICK REFERENCE CARDS
# Static content, zero API calls, loads instantly
# ============================================================

# QUICK_REFERENCE_CARDS → loaded from nac_contract_data.py

# ============================================================
# FEATURE 2: CANONICAL QUESTION LABELS
# Keyword matching only, no AI, no embeddings
# ============================================================

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
    """Classify by keyword matching. No AI, no embeddings."""
    q_lower = question_text.lower()
    best_match = None
    best_count = 0
    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > best_count:
            best_count = count
            best_match = category
    return best_match if best_match else "General Contract Question"

# ANSWER_MODIFIERS → loaded from nac_contract_data.py

def get_answer_modifier(category_label):
    """Return static modifier text. No AI."""
    if not category_label:
        return ANSWER_MODIFIERS["General"]
    for key in ANSWER_MODIFIERS:
        if key.lower() in category_label.lower():
            return ANSWER_MODIFIERS[key]
    return ANSWER_MODIFIERS["General"]

# ============================================================
# FEATURE 4: ANSWER RATING
# Logging only, no AI processing
# ============================================================

def log_rating(question_text, rating, contract_id, comment=""):
    """Log a rating via ContractLogger (Turso-backed)."""
    try:
        logger = init_logger()
        logger.log_rating(question_text, rating, contract_id, comment)
        return True
    except Exception:
        return False

# ============================================================
# SEMANTIC SIMILARITY CACHE
# ============================================================
# ============================================================
# SEMANTIC SIMILARITY CACHE — imported from cache_manager.py
# ============================================================
from cache_manager import SemanticCache, get_semantic_cache

# ============================================================
# INIT FUNCTIONS
# ============================================================

@st.cache_resource
def load_api_keys():
    import os
    keys = {}
    
    # Try environment variables first (Railway)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if anthropic_key and openai_key:
        keys['anthropic'] = anthropic_key
        keys['openai'] = openai_key
        return keys
    
    # Then try Streamlit secrets
    try:
        keys['openai'] = st.secrets["OPENAI_API_KEY"]
        keys['anthropic'] = st.secrets["ANTHROPIC_API_KEY"]
        return keys
    except Exception:
        pass
    
    # Then try file
    try:
        with open('api_key.txt', 'r') as f:
            for line in f:
                if 'OPENAI_API_KEY' in line:
                    keys['openai'] = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                if 'ANTHROPIC_API_KEY' in line:
                    keys['anthropic'] = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        return keys
    except FileNotFoundError:
        st.error("API keys not found. Set ANTHROPIC_API_KEY and OPENAI_API_KEY environment variables.")
        st.stop()
@st.cache_resource
def init_clients():
    keys = load_api_keys()
    openai_client = OpenAI(api_key=keys['openai'])
    anthropic_client = Anthropic(api_key=keys['anthropic'])
    return openai_client, anthropic_client

@st.cache_resource
def init_contract_manager():
    return ContractManager()

@st.cache_resource
def init_logger():
    return ContractLogger()

@st.cache_resource
def load_contract(contract_id):
    manager = init_contract_manager()
    chunks, embeddings = manager.load_contract_data(contract_id)
    return chunks, embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ============================================================
# BM25 KEYWORD SEARCH
# Catches exact contract terms that embeddings might miss.
# No external packages — pure Python implementation.
# ============================================================
# Contract-specific stopwords — common English words plus filler
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
    """Tokenize text for BM25. Preserves section numbers and hyphenated terms."""
    # Lowercase, split on whitespace and punctuation but keep hyphens and dots in terms
    tokens = re.findall(r'[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?', text.lower())
    return [t for t in tokens if t not in _BM25_STOPWORDS and len(t) > 1]

@st.cache_data(show_spinner=False)
def _build_bm25_index(_chunk_texts):
    """Pre-compute BM25 index from chunk texts. Cached so it only runs once."""
    # _chunk_texts is a tuple of strings (hashable for st.cache_data)
    doc_tokens = [_bm25_tokenize(text) for text in _chunk_texts]
    doc_count = len(doc_tokens)
    avg_dl = sum(len(d) for d in doc_tokens) / doc_count if doc_count > 0 else 1

    # Document frequency: how many docs contain each term
    df = {}
    for tokens in doc_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1)

    return doc_tokens, idf, avg_dl

def _bm25_search(query, chunks, top_n=15, k1=1.5, b=0.75):
    """Score all chunks against query using BM25. Returns top_n (score, chunk) pairs."""
    # Build index (cached after first call)
    chunk_texts = tuple(c['text'] for c in chunks)
    doc_tokens, idf, avg_dl = _build_bm25_index(chunk_texts)

    query_tokens = _bm25_tokenize(query)
    if not query_tokens:
        return []

    scores = []
    for i, tokens in enumerate(doc_tokens):
        dl = len(tokens)
        score = 0.0
        # Term frequency map for this doc
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

@st.cache_data(ttl=86400, show_spinner=False)
def get_embedding_cached(question_text, _openai_client):
    response = _openai_client.embeddings.create(
        input=question_text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# ============================================================
# FORCE-INCLUDE CHUNKS
# ============================================================

# FORCE_INCLUDE_RULES → loaded from nac_contract_data.py

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

# ============================================================
# CONTEXT PACKS — Curated essential pages per topic
# Guarantees the right provisions are always included.
# Embedding search supplements with anything unusual.
# ============================================================
# CONTEXT_PACKS → loaded from nac_contract_data.py

# Map question categories to context pack keys
# CATEGORY_TO_PACK → loaded from nac_contract_data.py

# Provision chains: keyword triggers → supplemental LOA/MOU pages
# These fire regardless of pack category to catch cross-references
# PROVISION_CHAINS → loaded from nac_contract_data.py

def get_pack_chunks(pack_key, all_chunks):
    """Get all chunks from a context pack's essential pages."""
    if pack_key not in CONTEXT_PACKS:
        return []
    pages = set(CONTEXT_PACKS[pack_key]['pages'])
    return [c for c in all_chunks if c['page'] in pages]

def classify_all_matching_packs(question_text):
    """Return all pack keys that match the question, ordered by match strength."""
    q_lower = question_text.lower()
    pack_scores = {}  # pack_key -> match count

    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > 0:
            pack_key = CATEGORY_TO_PACK.get(category)
            if pack_key and pack_key in CONTEXT_PACKS:
                pack_scores[pack_key] = max(pack_scores.get(pack_key, 0), count)

    # Sort by match strength descending
    sorted_packs = sorted(pack_scores.items(), key=lambda x: x[1], reverse=True)
    return [pk for pk, _ in sorted_packs]

def search_contract(question, chunks, embeddings, openai_client, max_chunks=75):
    question_embedding = get_embedding_cached(question, openai_client)
    question_lower = question.lower()
    forced_chunks = find_force_include_chunks(question_lower, chunks)

    # Cross-topic pack detection — find ALL matching packs
    matching_packs = classify_all_matching_packs(question)

    if matching_packs:
        # Merge pages from all matching packs
        merged_pages = set()
        for pk in matching_packs:
            merged_pages.update(CONTEXT_PACKS[pk]['pages'])

        # Provision chain injection — add LOA/MOU pages triggered by keywords
        chain_hits = []
        for keyword, chain_pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                merged_pages.update(chain_pages)
                chain_hits.append(keyword)

        pack_chunks = [c for c in chunks if c['page'] in merged_pages]
        print(f"[Search] PACK MODE: {matching_packs} | chains: {chain_hits} | pages: {len(merged_pages)} | chunks: {len(pack_chunks)}")

        # Multi-pack gets slightly higher cap; single pack stays at 30
        if len(matching_packs) > 1:
            max_total = 35
            embedding_top_n = 10
        else:
            max_total = CONTEXT_PACKS[matching_packs[0]].get('max_total', 30)
            embedding_top_n = CONTEXT_PACKS[matching_packs[0]].get('embedding_top_n', 15)

        # Rank pack chunks by relevance and trim
        max_pack = max_total - min(embedding_top_n, 5)
        if len(pack_chunks) > max_pack:
            # Build chunk ID → index lookup once
            id_to_idx = {c.get('id'): i for i, c in enumerate(chunks)}
            pack_scores = []
            for pc in pack_chunks:
                idx = id_to_idx.get(pc.get('id'))
                if idx is not None:
                    score = cosine_similarity(question_embedding, embeddings[idx])
                else:
                    score = 0
                pack_scores.append((score, pc))
            pack_scores.sort(reverse=True, key=lambda x: x[0])
            pack_chunks = [pc for _, pc in pack_scores[:max_pack]]
    else:
        # FALLBACK MODE: pure embedding search (General questions)
        # But still check provision chains for keyword-triggered pages
        chain_pages = set()
        chain_hits = []
        for keyword, pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                chain_pages.update(pages)
                chain_hits.append(keyword)
        if chain_pages:
            pack_chunks = [c for c in chunks if c['page'] in chain_pages]
            print(f"[Search] FALLBACK + CHAINS: {chain_hits} | pages: {len(chain_pages)} | chunks: {len(pack_chunks)}")
        else:
            pack_chunks = []
            print(f"[Search] FALLBACK — no packs, no chains matched")
        embedding_top_n = 30
        max_total = 30

    # Embedding search
    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))
    similarities.sort(reverse=True, key=lambda x: x[0])
    embedding_chunks = [chunk for score, chunk in similarities[:embedding_top_n]]

    # BM25 keyword search — catches exact terms embeddings miss
    bm25_top_n = min(10, embedding_top_n)
    bm25_results = _bm25_search(question, chunks, top_n=bm25_top_n)
    bm25_chunks = [chunk for score, chunk in bm25_results]

    # Merge: forced first, then pack, then BM25, then embedding — deduplicated
    seen_ids = set()
    merged = []

    for chunk in forced_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)

    for chunk in pack_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    for chunk in bm25_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    for chunk in embedding_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    # Log final result
    pages_sent = sorted(set(c['page'] for c in merged))
    print(f"[Search] FINAL: {len(merged)} chunks from pages {pages_sent[:15]}{'...' if len(pages_sent) > 15 else ''}")

    return merged

# ============================================================
# PRE-COMPUTED PAY CALCULATOR
# Extracts scenario details, does all math locally, injects
# results into API call so Sonnet explains — never calculates.
# ============================================================
def _build_pay_reference(question):
    """Extract pay scenario details and pre-compute all applicable pay values.
    Returns a text block to inject into the API call, or empty string."""
    q = question.lower()

    # Only trigger for pay-related questions
    pay_triggers = ['pay', 'paid', 'compensation', 'make', 'earn', 'rate', 'rig',
                    'dpg', 'premium', 'overtime', 'pch', 'wage', 'salary',
                    'junior assignment', 'ja ', 'open time', 'day off']
    if not any(t in q for t in pay_triggers):
        return ""

    # Extract position
    if 'captain' in q or 'capt ' in q:
        positions = ['Captain']
    elif 'first officer' in q or 'fo ' in q or 'f/o' in q:
        positions = ['First Officer']
    else:
        positions = ['Captain', 'First Officer']

    # Extract year
    year_match = re.search(r'year\s*(\d{1,2})', q)
    if not year_match:
        year_match = re.search(r'(\d{1,2})[\s-]*year', q)
    year = int(year_match.group(1)) if year_match and 1 <= int(year_match.group(1)) <= 12 else None

    # Extract numeric values for duty hours, block time, TAFD
    duty_hours = None
    block_hours = None
    tafd_hours = None

    # "12 hour duty" or "duty of 12 hours" or "12-hour duty day" or "duty for 12 hours"
    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:went|reached|hit|got|exceeded|was)\s*(?:to|up to)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hours = float(duty_match.group(1))

    # "block time of 5 hours" or "5 hours of block" or "flew 5 hours"
    block_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:block|flight|flying|flew)', q)
    if not block_match:
        block_match = re.search(r'(?:block|flight|flew)\s*(?:time)?\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if block_match:
        block_hours = float(block_match.group(1))

    # "TAFD of 24 hours" or "24 hours TAFD" or "away from domicile for 24 hours"
    tafd_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:tafd|away from domicile|time away)', q)
    if not tafd_match:
        tafd_match = re.search(r'(?:tafd|time away|away from domicile)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if tafd_match:
        tafd_hours = float(tafd_match.group(1))

    # Detect premium scenarios
    premiums = {}
    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        premiums['Junior Assignment 1st in 3mo (200%)'] = 2.00
        premiums['Junior Assignment 2nd in 3mo (250%)'] = 2.50
    if 'open time' in q and ('pick' in q or 'award' in q or 'volunt' in q):
        premiums['Open Time Pickup (150%)'] = 1.50
    if 'vacation' in q and ('cancel' in q or 'work' in q):
        premiums['Vacation Cancellation Work (200%)'] = 2.00
    if 'check airman' in q or 'instructor' in q or 'apd' in q:
        if 'day off' in q or 'day-off' in q:
            premiums['Check Airman Admin on Day Off (175%)'] = 1.75
    if 'hostile' in q:
        premiums['Hostile Area (200%)'] = 2.00

    # If we have no year and no numeric values, provide full rate table
    # so the model uses pre-computed rates instead of recalculating
    has_scenario = duty_hours or block_hours or tafd_hours

    # Build the reference
    lines = ["PRE-COMPUTED PAY REFERENCE (use these exact numbers — do not recalculate):"]
    lines.append(f"Current pay multiplier: DOS rate x 1.02^{PAY_INCREASES} = DOS x {PAY_MULTIPLIER:.5f}")
    lines.append("")

    # Show rates for applicable positions
    years_to_show = [year] if year else list(range(1, 13))
    for pos in positions:
        for y in years_to_show:
            dos = PAY_RATES_DOS['B737'][pos][y]
            current = round(dos * PAY_MULTIPLIER, 2)
            lines.append(f"B737 {pos} Year {y}: DOS {dos:.2f} → Current {current:.2f}/hour")

    # If scenario has numbers, compute all pay guarantees
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

            # DPG always applies
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

            # Determine greatest PCH
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

            # Apply premiums
            if premiums:
                lines.append("")
                lines.append("    WITH PREMIUMS:")
                for prem_name, mult in premiums.items():
                    prem_pay = round(best_pch * rate * mult, 2)
                    lines.append(f"    {prem_name}: {best_pch} PCH x {rate:.2f} x {mult} = {prem_pay:.2f}")

            lines.append("")

    return "\n".join(lines)

# ============================================================
# GRIEVANCE PATTERN DETECTOR
# Scans question for potential contract violation indicators
# and injects alerts so Sonnet addresses them proactively.
# ============================================================
def _detect_grievance_patterns(question):
    """Detect potential contract violation patterns in a scenario question.
    Returns a text block to inject into the API call, or empty string."""
    q = question.lower()
    alerts = []

    # --- DUTY TIME VIOLATIONS ---
    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if not duty_match:
        # "duty went to 15.5 hours" / "duty reached 17 hours" / "duty hit 16 hours"
        duty_match = re.search(r'duty\s*(?:went|reached|hit|got|exceeded|was)\s*(?:to|up to)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hrs = float(duty_match.group(1))
        if duty_hrs > 16:
            alerts.append(f"⚠️ DUTY TIME ALERT: {duty_hrs} hours exceeds the 16-hour maximum for a basic 2-pilot crew (Section 13.F.1). Verify crew complement — 18hr max for augmented (3-pilot), 20hr max for heavy (4-pilot). If exceeded, per Section 14.N, the Company must remove the pilot from the trip and place into rest.")
        elif duty_hrs > 14:
            alerts.append(f"⚠️ REST REQUIREMENT ALERT: {duty_hrs} hours of duty triggers the 12-hour minimum rest requirement (Section 13.G.1 — duty over 14 hours requires 12 hours rest, not the standard 10 hours).")

    # --- REST PERIOD VIOLATIONS ---
    rest_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:rest|off|between)', q)
    if rest_match:
        rest_hrs = float(rest_match.group(1))
        if rest_hrs < 10:
            alerts.append(f"⚠️ REST VIOLATION ALERT: {rest_hrs} hours of rest is below the 10-hour minimum required after duty of 14 hours or less (Section 13.G.1). This is a potential grievance.")
        elif rest_hrs < 12:
            alerts.append(f"⚠️ REST ALERT: {rest_hrs} hours rest — verify prior duty period length. If prior duty exceeded 14 hours, minimum rest is 12 hours, not 10 (Section 13.G.1).")

    # --- JUNIOR ASSIGNMENT ISSUES ---
    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        alerts.append("⚠️ JA CHECKLIST: Verify (1) inverse seniority order was followed (Section 14.O.1), (2) whether this is 1st or 2nd JA in rolling 3-month period for premium rate (Section 3.R), (3) one-extension-per-month limit if extended (Section 14.N.6).")
        if 'day off' in q:
            alerts.append("⚠️ DAY-OFF JA: Per Section 14.O, JA on a Day Off requires 200% premium (1st in 3mo) or 250% (2nd in 3mo). Verify the pilot was not senior to other available pilots.")

    # --- EXTENSION ISSUES ---
    if 'extend' in q or 'extension' in q:
        alerts.append("⚠️ EXTENSION CHECKLIST: Per Section 14.N — (1) only ONE involuntary extension per month is permitted, (2) extension cannot violate duty time limits (Section 13.F), (3) extension cannot cause a pilot to miss a scheduled Day Off beyond 0200 LDT (Section 15.A.7).")

    # --- DAY OFF ENCROACHMENT ---
    if 'day off' in q and ('work' in q or 'called' in q or 'schedul' in q or 'assign' in q or 'duty' in q):
        if 'ja' not in q and 'junior' not in q:  # JA already handled above
            alerts.append("⚠️ DAY-OFF WORK: Determine if this was a Junior Assignment (200%/250% per Section 3.R) or voluntary Open Time pickup (150% per Section 3.P). Assignments may be scheduled up to 0200 LDT into a Day Off (Section 15.A.7) — duty past 0200 into a Day Off is a potential violation.")

    # --- MINIMUM DAYS OFF ---
    if 'days off' in q and ('month' in q or 'line' in q or 'schedule' in q):
        alerts.append("⚠️ DAYS OFF MINIMUM: Per Section 14.E.2.d (LOA #15), minimum is 13 Days Off for a 30-day month and 14 Days Off for a 31-day month. Verify the published line meets this requirement.")

    # --- POSITIVE CONTACT ---
    if 'schedule change' in q or 'reassign' in q or 'no call' in q or 'no contact' in q or 'never called' in q or 'text message' in q or 'text only' in q or 'email only' in q or 'voicemail' in q or ('no phone' in q and 'call' in q) or ('text' in q and 'no call' in q) or ('changed' in q and ('text' in q or 'email' in q)):
        alerts.append("⚠️ POSITIVE CONTACT REQUIRED: Per MOU #2 (Page 381), schedule changes require Positive Contact via the pilot's authorized phone number. Email, text, or voicemail alone is NOT sufficient — the pilot must acknowledge the change verbally. Failure to make Positive Contact means the change is not effective.")

    # --- REST INTERRUPTION ---
    if 'rest' in q and ('interrupt' in q or 'call' in q or 'phone' in q or 'woke' in q or 'disturb' in q):
        alerts.append("⚠️ REST INTERRUPTION: Per Section 13.H.7, if a pilot's rest is interrupted (e.g., hotel security, repeated phone calls), the required rest period begins anew. Only emergency/security notifications are exempt from this rule.")

    # --- REASSIGNMENT ISSUES ---
    if 'reassign' in q and ('reserve' in q or 'r-1' in q or 'r-2' in q or 'r-3' in q or 'r-4' in q or 'r1' in q or 'r2' in q):
        alerts.append("⚠️ RESERVE REASSIGNMENT: Per MOU #4 (Page 383), Crew Scheduling cannot reassign a pilot performing a Trip Pairing to a Reserve Assignment. Reserve type changes require 12-hour notice (MOU #4 provision 8). If more than 2 pilots may be reassigned, inverse seniority applies (MOU #4 provision 13).")

    if not alerts:
        return ""

    header = "GRIEVANCE PATTERN ALERTS (address each applicable alert in your response):"
    return header + "\n" + "\n".join(alerts)


# ============================================================
# API CALL
# ============================================================
# ============================================================
# QUESTION COMPLEXITY ROUTER
# Routes questions to the right model tier:
#   SIMPLE  → Haiku (cheapest, ~0.3¢/question)
#   STANDARD → Sonnet (balanced, ~3.4¢/question)
#   COMPLEX  → Opus (smartest, ~20¢/question)
# ============================================================

# Model strings for each tier
MODEL_TIERS = {
    'simple': 'claude-haiku-4-5-20251001',
    'standard': 'claude-sonnet-4-20250514',
    'complex': 'claude-opus-4-20250514',
}

# Indicators that a question is COMPLEX — needs Opus-level reasoning
_COMPLEX_INDICATORS = [
    # Pay scenarios with specific numbers
    'what do i get paid', 'what would i get paid', 'what should i get paid',
    'what am i owed', 'how much should i be paid', 'calculate my pay',
    # Duty crossing into day off (overtime scope disputes)
    'into my day off', 'into a day off', 'past my day off',
    'extended into', 'crossed into',
    # Multi-provision scenarios
    'extended and', 'junior assigned and', 'on reserve and',
    # Explicit ambiguity / grievance strength questions
    'is this a grievance', 'should i grieve', 'do i have a grievance',
    'contract violation', 'violated the contract', 'violate the contract',
    # Complex comparisons
    'difference between', 'compared to', 'which is better',
    'what are my options', 'what are all the',
]

# Indicators that a question is SIMPLE — Haiku can handle it
_SIMPLE_PATTERNS = [
    # Section/location lookups
    r'^what section (?:covers|talks about|addresses|is about)',
    r'^where (?:can i find|does it talk about|is the section)',
    r'^which section',
    r'^what page',
    # Simple yes/no contract questions
    r'^(?:does|is|can|are) (?:the contract|there a)',
    # Single-word definition lookups that didn't match Tier 1
    r'^what (?:is|are) (?:a |an |the )?[\w\s]{1,25}\??$',
]

_SIMPLE_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]

def _classify_complexity(question_lower, matching_packs=None, has_pay_ref=False, has_grievance_ref=False, conversation_history=None):
    """Classify question complexity for model routing.
    
    Returns: 'simple', 'standard', or 'complex'
    """
    # --- COMPLEX CHECKS (most expensive model, most reasoning needed) ---
    
    # 1. Multiple scenario indicators with numbers = complex pay calculation
    scenario_count = 0
    scenario_keywords = ['duty', 'block', 'flew', 'hours', 'day off', 'overtime',
                         'extension', 'junior assign', 'reserve', 'rap']
    for kw in scenario_keywords:
        if kw in question_lower:
            scenario_count += 1
    has_numbers = bool(re.search(r'\d+(?:\.\d+)?\s*(?:hours?|hr|pch|am|pm)', question_lower))
    has_times = bool(re.search(r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|noon|midnight|\d{4}\s*(?:ldt|local|zulu)', question_lower))
    
    # Scenario with numbers AND multiple topics = complex
    if has_numbers and scenario_count >= 2:
        return 'complex'
    
    # Time references with pay/overtime = complex
    if has_times and any(kw in question_lower for kw in ['pay', 'paid', 'overtime', 'premium', 'owed']):
        return 'complex'
    
    # 2. Explicit complex indicators
    if any(ind in question_lower for ind in _COMPLEX_INDICATORS):
        return 'complex'
    
    # 3. Pre-computed pay reference fired AND grievance pattern fired = complex
    if has_pay_ref and has_grievance_ref:
        return 'complex'
    
    # 4. Cross-topic questions (multiple context packs matched)
    if matching_packs and len(matching_packs) >= 2:
        # Multi-pack + numbers = definitely complex
        if has_numbers or has_times:
            return 'complex'
        # Multi-pack without numbers = standard (e.g., "tell me about reserve and scheduling")
        return 'standard'
    
    # 5. Follow-up on a complex conversation — only if this looks like a follow-up
    if conversation_history and len(conversation_history) >= 2:
        last_answer = conversation_history[-1].get('answer', '')
        if 'AMBIGUOUS' in last_answer or 'OVERTIME SCOPE DISPUTE' in last_answer:
            # Only escalate if this looks like a follow-up (short, uses follow-up language)
            follow_up_signals = ['what if', 'what about', 'and if', 'but what if',
                                 'in that case', 'same scenario', 'same situation',
                                 'follow up', 'followup', 'you said', 'you mentioned',
                                 'what would change', 'does that mean']
            is_short = len(question_lower.split()) <= 15
            has_follow_up = any(sig in question_lower for sig in follow_up_signals)
            if is_short and has_follow_up:
                return 'complex'
    
    # --- SIMPLE CHECKS (cheapest model) ---
    
    # Short questions with simple patterns
    if len(question_lower.split()) <= 10:
        for pattern in _SIMPLE_COMPILED:
            if pattern.search(question_lower):
                return 'simple'
    
    # Single topic, no numbers, no scenarios = simple
    if scenario_count == 0 and not has_numbers and not has_times:
        if not has_pay_ref and not has_grievance_ref:
            # Very short questions are usually simple lookups
            if len(question_lower.split()) <= 8:
                return 'simple'
    
    # --- DEFAULT: STANDARD ---
    return 'standard'


def _ask_question_api(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    start_time = time.time()

    relevant_chunks = search_contract(question, chunks, embeddings, openai_client)

    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # Detect pay and grievance references (needed for routing AND injection)
    pay_ref = _build_pay_reference(question)
    grievance_ref = _detect_grievance_patterns(question)

    # Route question to the right model tier
    matching_packs = classify_all_matching_packs(question)
    model_tier = _classify_complexity(
        question.lower(),
        matching_packs=matching_packs,
        has_pay_ref=bool(pay_ref),
        has_grievance_ref=bool(grievance_ref),
        conversation_history=conversation_history,
    )
    model_name = MODEL_TIERS[model_tier]

    # Detect if pay-related content is needed (used for prompt trimming and logging)
    q_lower = question.lower()
    is_pay_question = any(kw in q_lower for kw in [
        'pay', 'paid', 'compensation', 'wage', 'salary', 'rate', 'pch',
        'rig', 'dpg', 'premium', 'overtime', 'owed', 'earn',
        'junior assign', 'ja ', 'open time', 'day off',
        'block', 'duty', 'tafd', 'flew', 'flying', 'hours'
    ])

    print(f"[Router] {model_tier.upper()} → {model_name} | Q: {question[:80]}")
    if model_tier != 'simple':
        print(f"[Prompt] Pay sections: {'INJECTED' if is_pay_question else 'SKIPPED'} | max_tokens: {2000 if model_tier == 'complex' else 1500}")

    # --- BUILD SYSTEM PROMPT (tiered by complexity) ---
    
    if model_tier == 'simple':
        # Haiku gets a compact prompt — just the essentials
        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA).

SCOPE: This tool ONLY searches the {airline_name} JCBA. No FARs, company manuals, or other policies.

RULES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Use neutral language ("the contract states" not "you get")
4. Acknowledge when the contract is silent

STATUS: 🔵 CLEAR (unambiguous answer), 🔵 AMBIGUOUS (multiple interpretations), 🔵 NOT ADDRESSED (no relevant language)

FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
📝 EXPLANATION: [Plain English]
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

FORMATTING RULES:
- Do NOT use markdown headings (#, ##, ###) — they render too large
- Use **bold text** for sub-topics and labels instead
- Keep answers compact and professional
- Do NOT add a title or heading at the top of your answer
- Do NOT use dollar signs ($) — write amounts without them (Streamlit renders $ as LaTeX)."""
        max_tokens = 1000
    else:
        # Sonnet and Opus get the full system prompt
        # Pay-specific prompt sections — only injected when relevant
        pay_prompt_sections = ""
        if is_pay_question:
            pay_prompt_sections = """
CURRENT PAY RATES:
DOS = July 24, 2018. Per Section 3.B.3, rates increase 2% annually on DOS anniversary. As of today: {PAY_INCREASES} increases (July 2019–July {2018 + PAY_INCREASES}). CURRENT RATE = Appendix A DOS rate × {PAY_MULTIPLIER:.5f}. Always use DOS column, multiply by {PAY_MULTIPLIER:.5f}, show math. If longevity year is stated, look up that rate in Appendix A and calculate. Do NOT say you cannot find the rate if a year is provided.

PAY QUESTION RULES:
When pay/compensation is involved:
- Identify position and longevity year if provided
- Calculate ALL four pay provisions and compare:
  1. Block PCH: [flight time]
  2. Duty Rig: [total duty hours] ÷ 2 = [X] PCH (if exact times unknown, show "Minimum Duty Rig estimate" using available info — NEVER say "cannot calculate")
  3. DPG: 3.82 PCH
  4. Trip Rig: [TAFD hours] ÷ 4.9 = [X] PCH (or "Not applicable — single-day duty period")
  → Pilot receives the GREATER of these
- Show all math: PCH values AND dollar amounts
- Do NOT use dollar signs ($) — write "191.22/hour" not "$191.22/hour" (Streamlit renders $ as LaTeX)
- End with: "The pilot should be paid [X] PCH × [rate] = [total]"

DUTY RIG ESTIMATION: If exact times are missing, calculate minimum estimate from what IS known. For assigned trips: duty starts minimum 1 hour before departure. For reserve: duty starts at RAP DOT or 1 hour before departure (whichever earlier). Always provide estimate.

OVERTIME PREMIUM (Section 3.Q.1):
150% pay for duty on scheduled Day Off applies ONLY when caused by: (a) circumstances beyond Company control (weather, mechanical, ATC, customer accommodation), OR (b) assignment to remain with aircraft for repairs.
- If cause is NOT stated: quote trigger conditions, present 150% as CONDITIONAL, mark AMBIGUOUS
- Do NOT automatically apply 150% without a stated trigger
- OVERTIME SCOPE DISPUTE (REQUIRED ONLY when a single duty period begins on a workday and extends into a Day Off): "⚠️ OVERTIME SCOPE DISPUTE: Even if the 150% premium applies, the contract does not specify whether it covers all PCH earned in the duty period or only the PCH attributable to the Day Off hours. Both interpretations are reasonable, and this is a potential area of dispute."
  Do NOT include this dispute paragraph when duty is entirely on a Day Off (e.g., Junior Assignment, full Day Off duty). The scope dispute only exists when there is a split between workday hours and Day Off hours within the same duty period.

RESERVE PAY:
- R-1 and R-2 are DUTY — duty starts at scheduled RAP DOT, not when called or when flight departs
- Use FULL duty period for Duty Rig: from RAP DOT or 1hr before departure (whichever earlier) to release
- Per Section 3.F.1.b: Reserve Pilot receives GREATER of DPG or PCH from assigned trip
- If duty extends past RAP or into Day Off, you MUST address: extension analysis, 0200 LDT rule (15.A.7-8), overtime premium eligibility, and whether single duty period = one Workday (Section 3.D.2)
"""

        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA). Provide accurate, unbiased analysis based solely on contract language provided.

SCOPE: This tool ONLY searches the {airline_name} JCBA. It has NO access to FARs, company manuals/SOPs, company policies/memos, other labor agreements, or employment laws. If asked about these, state: "This tool only searches the {airline_name} pilot contract (JCBA) and cannot answer questions about FAA regulations, company manuals, or other policies outside the contract."

CONVERSATION CONTEXT: Use conversation history for follow-ups. Maintain same position, aircraft type, and parameters unless explicitly changed. Always provide complete answers with full citations even for follow-ups.

CORE PRINCIPLES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Never assume provisions exist that are not in the provided text
4. Use neutral language ("the contract states" not "you get" or "company owes")
5. Acknowledge when the contract is silent; cite all applicable provisions
6. Read ALL provided sections before answering — look across pay, scheduling, reserve, and hours of service

ANALYSIS RULES:
- Check for defined terms — many words have specific contract definitions
- Note qualifiers: "shall" vs "may", "except", "unless", "notwithstanding", "provided"
- Distinguish: "scheduled" vs "actual", "assigned" vs "awarded"
- Distinguish pilot categories: Regular Line, Reserve (R-1/R-2/R-3/R-4), Composite, TDY, Domicile Flex
- Distinguish assignment types: Trip Pairings, Reserve Assignments, Company-Directed, Training, Deadhead

KEY DEFINITIONS (from Section 2):
- Block Time = Brakes released to brakes set. Flight Time = Brake release to block in.
- Day = Calendar Day 00:00–23:59 LDT. Day Off = Scheduled Day free of ALL Duty at Domicile.
- DPG = 3.82 PCH minimum per Day of scheduled Duty.
- Duty Period = Continuous time from Report for Duty until Released and placed into Rest. Rest Period ≠ Day Off.
- Duty Rig = 1 PCH per 2 hours Duty, prorated minute-by-minute. Trip Rig = TAFD ÷ 4.9.
- Extension = Involuntary additional Flight/Duty after last segment of Trip Pairing.
- FIFO = First In, First Out reserve scheduling per Section 15.
- JA = Junior Assignment: involuntary Duty on Day Off, inverse seniority (most junior first).
- PCH = Pay Credit Hours — the unit of compensation.
- R-1 = In-Domicile Short Call (Duty). R-2 = Out-of-Domicile Short Call (Duty). R-3 = Long Call. R-4 = Airport RAP (Duty).
- Composite Line = Blank line constructed after SAP. Domicile Flex Line = Reserve with 13+ consecutive Days Off, all Workdays R-1.
- Ghost Bid = Line a Check Airman bids but cannot be awarded; sets new MPG.
- Phantom Award = Bidding higher-paying Position per seniority to receive that pay rate.
{pay_prompt_sections}
SCHEDULING/REST RULES:
- Check across Section 13 (Hours of Service), Section 14 (Scheduling), Section 15 (Reserve)
- Different line types have different rules — cite which line type each provision applies to
- Distinguish "Day Off" (defined term) from "Rest Period" (defined term)

STATUS DETERMINATION:
🔵 CLEAR = Contract explicitly and unambiguously answers; no conflicting provisions
🔵 AMBIGUOUS = Multiple interpretations possible, conflicting provisions, missing scenario details needed to determine which rule applies, or premium trigger conditions not confirmed
🔵 NOT ADDRESSED = Contract contains no relevant language

RESPONSE FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
(Repeat for each provision)
📝 EXPLANATION: [Plain English analysis]
  Include ⏰ EXTENSION / DAY OFF DUTY ANALYSIS when duty crosses past RAP or into Day Off
  Include ⚠️ OVERTIME SCOPE DISPUTE only when duty starts on a workday and extends into a Day Off (not for pure Day Off duty like JA)
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence justification]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

FORMATTING RULES:
- Do NOT use markdown headings (#, ##, ###) — they render too large in the UI
- Use **bold text** for sub-topics and labels instead (e.g., **Accrual:** not ## ACCRUAL)
- Do NOT add a title or heading at the top of your answer — just start with the content
- Keep answers compact, professional, and easy to scan
- Use short paragraphs, not walls of text

Every claim must trace to a specific quoted provision. Do not speculate about "common practice" or reference external laws unless the contract itself references them.

Do NOT use dollar signs ($) — write amounts without them (Streamlit renders $ as LaTeX)."""
        # Standard gets 1500, Complex gets 2000
        max_tokens = 2000 if model_tier == 'complex' else 1500

    messages = []

    # Add last 3 Q&A pairs as conversation context (questions and answers only, no chunks)
    if conversation_history:
        recent = conversation_history[-3:]
        for qa in recent:
            messages.append({
                "role": "user",
                "content": f"PREVIOUS QUESTION: {qa['question']}"
            })
            messages.append({
                "role": "assistant",
                "content": qa['answer']
            })

    user_content = f"""CONTRACT SECTIONS:
{context}

QUESTION: {question}
"""

    # Inject pre-computed pay reference if applicable (already computed above for routing)
    if pay_ref:
        user_content += f"\n{pay_ref}\n"

    # Inject grievance pattern alerts if applicable (already computed above for routing)
    if grievance_ref:
        user_content += f"\n{grievance_ref}\n"

    user_content += "\nAnswer:"

    messages.append({"role": "user", "content": user_content})

    message = anthropic_client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral", "ttl": "1h"}
            }
        ],
        messages=messages
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

# PAY_RATES_DOS, PAY_INCREASES, PAY_MULTIPLIER → loaded from nac_contract_data.py

# Auto-invalidate cached pay answers when PAY_INCREASES changes (every July)
def _check_pay_cache_freshness():
    """Compare stored PAY_INCREASES against current. If different, purge pay cache entries."""
    try:
        cache = get_semantic_cache()
        stored = cache.get_meta('pay_increases')
        current = str(PAY_INCREASES)
        if stored != current:
            pay_categories = [
                "Pay → Hourly Rate",
                "Pay → Daily Pay Guarantee",
                "Pay → Duty Rig",
                "Pay → Trip Rig / TAFD",
                "Pay → Overtime / Premium",
                "Pay → Junior Assignment Premium",
                "Pay → General Calculation",
            ]
            total_cleared = 0
            for cat in pay_categories:
                total_cleared += cache.clear_category('nac_jcba', cat)
            cache.set_meta('pay_increases', current)
            print(f"[Pay Cache] PAY_INCREASES changed ({stored} → {current}). Purged {total_cleared} stale pay entries.")
        else:
            print(f"[Pay Cache] PAY_INCREASES unchanged ({current}). Cache is fresh.")
    except Exception as e:
        print(f"[Pay Cache] Freshness check failed: {e}")

_check_pay_cache_freshness()

# DEFINITIONS_LOOKUP → loaded from nac_contract_data.py

# Fixed-value contract rules for instant lookup (no API call)
# TIER1_RULES → loaded from nac_contract_data.py

# Per diem is computed dynamically based on current date
def _get_per_diem_answer():
    """Build per diem Tier 1 answer with current rates based on anniversary increases."""
    dos_date = datetime(2018, 7, 24)
    now = datetime.now()
    # Count anniversaries: each July 24 after DOS
    anniversaries = now.year - dos_date.year
    if (now.month, now.day) < (dos_date.month, dos_date.day):
        anniversaries -= 1
    anniversaries = max(0, anniversaries)

    base_domestic = 56
    base_international = 72
    current_domestic = base_domestic + anniversaries
    current_international = base_international + anniversaries

    return f"""📄 CONTRACT LANGUAGE: "For Duty or other Company-Directed Assignments that are performed within the Contiguous United States, including all time during a layover in the United States, Fifty-Six Dollars ($56) per Day."
📍 Section 6.C.2.a, Page 99

"For Duty or other Company-directed Assignment that contains a segment that is to or from an airport outside the contiguous United States, including all layover time in a location outside of the contiguous United States: Seventy-Two Dollars ($72) per Day."
📍 Section 6.C.2.b, Page 100

"The Per Diem rates, as provided in subparagraph 6.C., shall be increased by one (1) Dollar ($1.00) per Day on each anniversary date of the Agreement."
📍 Section 6.C.2.c, Page 100

📝 EXPLANATION: Per the contract, pilots receive Per Diem for duty assignments that include rest periods away from their domicile. The base rates (DOS July 24, 2018) were 56/day domestic and 72/day international. Per Section 6.C.2.c, rates increase by 1/day on each contract anniversary.

As of today, there have been {anniversaries} anniversary increases (July 2019 through July {dos_date.year + anniversaries}):
- Domestic (contiguous U.S.): 56 + {anniversaries} = **{current_domestic}/day**
- International: 72 + {anniversaries} = **{current_international}/day**

Per Diem is calculated from the time of scheduled or actual report time at Domicile (whichever is later) until the scheduled or actual conclusion of duty at Domicile (whichever is later). Per Diem is only paid for assignments that include a rest period away from Domicile (Section 6.C.1).

🔵 STATUS: CLEAR - The contract explicitly states per diem rates in Section 6.C.2 and the annual increase formula in Section 6.C.2.c.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

# PER_DIEM_KEYWORDS → loaded from nac_contract_data.py

def _match_tier1_rule(question_lower):
    """Check if a question matches a Tier 1 fixed-value rule.
    Returns the rule key or None."""
    for rule_key, rule in TIER1_RULES.items():
        if any(kw in question_lower for kw in rule['keywords']):
            return rule_key
    return None

def _parse_pay_question(question_lower):
    """Parse a pay rate question and return (aircraft, position, year) or None."""
    # Extract year
    year_match = re.search(r'year\s*(\d{1,2})', question_lower)
    if not year_match:
        # Try "12 year" or "12-year"
        year_match = re.search(r'(\d{1,2})[\s-]*year', question_lower)
    if not year_match:
        return None
    year = int(year_match.group(1))
    if year < 1 or year > 12:
        return None

    # Extract position
    if 'captain' in question_lower or 'capt' in question_lower:
        position = 'Captain'
    elif 'first officer' in question_lower or 'fo ' in question_lower or 'f/o' in question_lower:
        position = 'First Officer'
    else:
        position = None

    # Extract aircraft — NAC only flies B737
    aircraft = 'B737'

    return aircraft, position, year

def _format_pay_answer(aircraft, position, year):
    """Build a formatted pay rate answer matching the app's output style."""
    # Determine which positions to show
    if position:
        combos = [(aircraft, position)]
    else:
        combos = [(aircraft, 'Captain'), (aircraft, 'First Officer')]

    rate_lines = []
    citation_parts = []

    for ac, pos in combos:
        dos_rate = PAY_RATES_DOS[ac][pos][year]
        current_rate = round(dos_rate * PAY_MULTIPLIER, 2)
        citation_parts.append(f'{pos} Year {year}: DOS rate {dos_rate:.2f}')
        rate_lines.append(f'- {pos} Year {year}: DOS rate {dos_rate:.2f} x 1.02^{PAY_INCREASES} ({PAY_MULTIPLIER:.5f}) = {current_rate:.2f} per hour')

    citation_text = '; '.join(citation_parts)

    answer = f"""📄 CONTRACT LANGUAGE: "B737 {citation_text}" 📍 Appendix A, Page 66

"On the Amendable Date of this Agreement and every anniversary thereafter until the Effective Date of an amended Agreement, Hourly Pay Rates shall increase by two percent (2%)." 📍 Section 3.B.3, Page 50

📝 EXPLANATION: The contract provides B737 Year {year} pay rates in Appendix A. The Date of Signing (DOS) is July 24, 2018. Per Section 3.B.3, pay rates increase by 2% annually on each anniversary. As of February 2026, there have been {PAY_INCREASES} annual increases (July 2019 through July 2025), so the current rates are:

{chr(10).join(rate_lines)}

🔵 STATUS: CLEAR - The contract explicitly provides the DOS pay rates in Appendix A and the annual increase formula in Section 3.B.3.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def _format_definition_answer(term, definition):
    """Build a formatted definition answer matching the app's output style."""
    display_term = term.upper() if len(term) <= 4 else term.title()

    answer = f"""📄 CONTRACT LANGUAGE: "{display_term}: {definition}" 📍 Section 2 (Definitions), Pages 13-45

📝 EXPLANATION: Per Section 2 (Definitions) of the contract, **{display_term}** is defined as: {definition}

🔵 STATUS: CLEAR - The contract explicitly defines this term in Section 2.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def tier1_instant_answer(question_lower):
    """
    Check if a question can be answered instantly without API call.
    Returns (answer, status, response_time) or None if not a Tier 1 question.
    """
    start = time.time()

    # --- TIER 1 RULE LOOKUPS (check BEFORE scenario detection) ---
    # These are "what is the rule?" questions that match keywords also
    # found in scenarios, so they must be checked first.
    # Only triggers on clean rule-lookup phrasing, not scenario context.
    rule_key = _match_tier1_rule(question_lower)
    if rule_key:
        # Extra guard: if the question contains specific numeric scenario details,
        # fall through to the API instead (e.g., "I had 8 hours rest after 16 hour duty")
        has_numeric_scenario = re.search(r'\d+(?:\.\d+)?\s*hours?\s*(?:of\s+)?(?:duty|rest|block|on duty)', question_lower)
        if not has_numeric_scenario:
            answer = TIER1_RULES[rule_key]['answer']
            return answer, 'CLEAR', round(time.time() - start, 1)

    # --- PER DIEM (computed dynamically based on current date) ---
    if any(kw in question_lower for kw in PER_DIEM_KEYWORDS):
        answer = _get_per_diem_answer()
        return answer, 'CLEAR', round(time.time() - start, 1)

    # --- SCENARIO DETECTION: If question has duty/block/TAFD numbers, skip Tier 1 ---
    # These need the full API with pre-computed pay calculator
    scenario_indicators = ['duty', 'block', 'tafd', 'flew', 'flying', 'flight time',
                           'time away', 'junior assign', 'ja ', 'open time pick',
                           'extension', 'reassign', 'day off', 'overtime',
                           'hour duty', 'hour block', 'hours of duty', 'hours of block',
                           'landed', 'released', 'departed', 'called at', 'got called',
                           'departure', 'what do i get paid', 'what would i get paid',
                           'what should i get paid', 'what am i owed',
                           'rap was', 'rap from', 'my rap', 'on reserve']
    has_scenario = any(s in question_lower for s in scenario_indicators)
    # Also catch time references: "3pm", "noon", "midnight", "0600", etc.
    if not has_scenario:
        has_scenario = bool(re.search(r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|noon|midnight|\d{4}\s*(?:ldt|local|zulu)', question_lower))
    if has_scenario:
        return None

    # --- PAY RATE QUESTIONS ---
    pay_keywords = ['pay rate', 'hourly rate', 'make per hour', 'paid per hour',
                    'how much', 'what rate', 'what is the rate', 'what\'s the rate',
                    'captain rate', 'fo rate', 'first officer rate', 'captain pay',
                    'fo pay', 'first officer pay', 'pay scale']

    if any(kw in question_lower for kw in pay_keywords):
        parsed = _parse_pay_question(question_lower)
        if parsed:
            aircraft, position, year = parsed
            answer = _format_pay_answer(aircraft, position, year)
            return answer, 'CLEAR', round(time.time() - start, 1)

    # Also catch "year X captain/FO" patterns even without explicit pay keywords
    if re.search(r'year\s*\d{1,2}\s*(captain|capt|first officer|fo |f/o)', question_lower) or \
       re.search(r'\d{1,2}[\s-]*year\s*(captain|capt|first officer|fo |f/o)', question_lower):
        parsed = _parse_pay_question(question_lower)
        if parsed:
            aircraft, position, year = parsed
            answer = _format_pay_answer(aircraft, position, year)
            return answer, 'CLEAR', round(time.time() - start, 1)

    # --- DEFINITION QUESTIONS ---
    def_patterns = [
        r'what (?:does|is|are|do)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*(?:mean|stand for|definition)',
        r'define\s+["\']?(.+?)["\']?\s*$',
        r'what (?:is|are)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*(?:in the contract|per the contract|according to)',
        r'what (?:is|are)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*\??\s*$',
    ]

    for pattern in def_patterns:
        match = re.search(pattern, question_lower.strip().rstrip('?'))
        if match:
            term = match.group(1).strip().lower()
            # Remove trailing words that aren't part of the term
            term = re.sub(r'\s+(mean|means|stand|stands|defined|definition).*$', '', term)
            if term in DEFINITIONS_LOOKUP:
                answer = _format_definition_answer(term, DEFINITIONS_LOOKUP[term])
                return answer, 'CLEAR', round(time.time() - start, 1)
            # Try partial match for multi-word terms
            for def_term, definition in DEFINITIONS_LOOKUP.items():
                if term == def_term or (len(term) > 3 and term in def_term):
                    answer = _format_definition_answer(def_term, definition)
                    return answer, 'CLEAR', round(time.time() - start, 1)

    return None

# ============================================================
# QUESTION PREPROCESSOR
# Normalizes pilot shorthand, abbreviations, and slang before
# the question hits Tier 1, BM25, embeddings, and the API.
# ============================================================

# Order matters: longer patterns first to avoid partial replacements
_SHORTHAND_MAP = [
    # Contractions and informal
    (r"\bwhats\b", "what is"),
    (r"\bwhat's\b", "what is"),
    (r"\bhow's\b", "how is"),
    (r"\bcan't\b", "cannot"),
    (r"\bdon't\b", "do not"),
    (r"\bdoesn't\b", "does not"),
    (r"\bwon't\b", "will not"),
    (r"\bdidn't\b", "did not"),
    (r"\bwasn't\b", "was not"),
    (r"\bi'm\b", "i am"),
    (r"\bi've\b", "i have"),
    (r"\bi'd\b", "i would"),
    # Pilot shorthand — positions
    (r"\bca\b", "captain"),
    (r"\bcapt\b", "captain"),
    (r"\bfo\b", "first officer"),
    (r"\bf/o\b", "first officer"),
    (r"\bpic\b", "pilot in command"),
    (r"\bsic\b", "second in command"),
    # Reserve types
    (r"\br1\b", "r-1"),
    (r"\br2\b", "r-2"),
    (r"\br3\b", "r-3"),
    (r"\br4\b", "r-4"),
    # Pilot shorthand — operations
    (r"\bja'd\b", "junior assigned"),
    (r"\bja'ed\b", "junior assigned"),
    (r"\bjaed\b", "junior assigned"),
    (r"\bja\b", "junior assignment"),
    (r"\bext'd\b", "extended"),
    (r"\bexted\b", "extended"),
    (r"\bdeadhd\b", "deadhead"),
    (r"\bdh\b", "deadhead"),
    (r"\bd/h\b", "deadhead"),
    (r"\bmx\b", "mechanical"),
    (r"\bmech\b", "mechanical"),
    (r"\bpax\b", "passenger"),
    (r"\bsked\b", "schedule"),
    (r"\bskd\b", "schedule"),
    (r"\bdom\b", "domicile"),
    (r"\bvac\b", "vacation"),
    (r"\bprobat\b", "probation"),
    (r"\bgriev\b", "grievance"),
    # Time/pay shorthand
    (r"\byr\b", "year"),
    (r"\byrs\b", "years"),
    (r"\bhr\b", "hour"),
    (r"\bhrs\b", "hours"),
    (r"\bmos?\b", "months"),
    (r"\bOT\b", "overtime"),
    (r"\bot\b", "overtime"),
    # Contract references
    (r"\bsect\b", "section"),
    (r"\bsec\b", "section"),
    (r"\bart\b", "article"),
    (r"\bloa\b", "loa"),
    (r"\bmou\b", "mou"),
    (r"\bjcba\b", "contract"),
    (r"\bcba\b", "contract"),
    # Aircraft
    (r"\b73\b", "b737"),
    (r"\b737\b", "b737"),
    (r"\b76\b", "b767"),
    (r"\b767\b", "b767"),
    # Common misspellings
    (r"\bscheudle\b", "schedule"),
    (r"\bschedual\b", "schedule"),
    (r"\bgrievence\b", "grievance"),
    (r"\bgreivance\b", "grievance"),
    (r"\bassigment\b", "assignment"),
    (r"\breassigment\b", "reassignment"),
    (r"\bpayed\b", "paid"),
    (r"\brecieve\b", "receive"),
    (r"\bcapatin\b", "captain"),
    (r"\bcompensaton\b", "compensation"),
    (r"\bextention\b", "extension"),
    (r"\bdomocile\b", "domicile"),
    (r"\bsenority\b", "seniority"),
    (r"\bseniortiy\b", "seniority"),
    # Additional pilot abbreviations
    (r"\bslb\b", "sick leave bank"),
    (r"\birop\b", "irregular operations"),
    (r"\birops\b", "irregular operations"),
    (r"\bsap\b", "schedule adjustment period"),
    (r"\bmpg\b", "monthly pay guarantee"),
    (r"\bpcd\b", "portable communications device"),
    (r"\bcrew sked\b", "crew scheduling"),
    (r"\bcrewsked\b", "crew scheduling"),
    (r"\bexco\b", "executive council"),
    (r"\balpa\b", "union"),
    (r"\bioe\b", "initial operating experience"),
    (r"\bfars\b", "federal aviation regulations"),
    (r"\bldt\b", "local domicile time"),
]

# Pre-compile patterns for performance
_SHORTHAND_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _SHORTHAND_MAP]

def preprocess_question(question_text):
    """Normalize pilot shorthand and abbreviations for better matching."""
    result = question_text
    for pattern, replacement in _SHORTHAND_COMPILED:
        result = pattern.sub(replacement, result)
    # Collapse multiple spaces
    result = re.sub(r'  +', ' ', result).strip()
    return result

# ============================================================
# MAIN ENTRY
# ============================================================
def ask_question(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    normalized = preprocess_question(question.strip()).lower()

    # Tier 1: Instant answers — no API cost, no embedding cost
    tier1_result = tier1_instant_answer(normalized)
    if tier1_result is not None:
        return tier1_result

    # Always check cache first — regardless of conversation history
    question_embedding = get_embedding_cached(normalized, openai_client)
    semantic_cache = get_semantic_cache()
    cached_result = semantic_cache.lookup(question_embedding, contract_id)
    if cached_result is not None:
        cached_answer, cached_status, cached_time = cached_result
        return cached_answer, cached_status, 0.0

    answer, status, response_time, model_tier = _ask_question_api(
        normalized, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history
    )

    # Only cache CLEAR and AMBIGUOUS answers — never cache NOT_ADDRESSED
    # A NOT_ADDRESSED might be a retrieval miss; next attempt could succeed
    if status != 'NOT_ADDRESSED':
        category = classify_question(normalized)
        semantic_cache.store(question_embedding, normalized, answer, status, response_time, contract_id, category)

    # "Did you mean?" — append suggestions when NOT_ADDRESSED
    if status == 'NOT_ADDRESSED':
        suggestions = _get_did_you_mean(normalized)
        if suggestions:
            answer += suggestions

    return answer, status, response_time


def _get_did_you_mean(question_lower):
    """Suggest related Quick Reference Cards and Tier 1 topics for NOT_ADDRESSED answers."""
    suggestions = []

    # Map keywords to Quick Reference Card titles
    qrc_matches = {
        'pay': ['Pay Calculation Guide', 'What is a Pay Discrepancy?'],
        'paid': ['Pay Calculation Guide', 'What is a Pay Discrepancy?'],
        'rate': ['Pay Calculation Guide'],
        'rig': ['Pay Calculation Guide'],
        'dpg': ['Pay Calculation Guide'],
        'overtime': ['Pay Calculation Guide', 'Extension Rules'],
        'premium': ['Pay Calculation Guide', 'Junior Assignment Rules'],
        'reserve': ['Reserve Types & Definitions'],
        'r-1': ['Reserve Types & Definitions'],
        'r-2': ['Reserve Types & Definitions'],
        'r-3': ['Reserve Types & Definitions'],
        'r-4': ['Reserve Types & Definitions'],
        'fifo': ['Reserve Types & Definitions'],
        'day off': ['Minimum Days Off / Availability', 'Junior Assignment Rules'],
        'days off': ['Minimum Days Off / Availability'],
        'schedule': ['Minimum Days Off / Availability'],
        'line': ['Minimum Days Off / Availability'],
        'extension': ['Extension Rules'],
        'extended': ['Extension Rules'],
        'junior assign': ['Junior Assignment Rules'],
        'ja ': ['Junior Assignment Rules'],
        'grievance': ['How to File a Grievance', 'What Evidence to Save'],
        'grieve': ['How to File a Grievance', 'What Evidence to Save'],
        'dispute': ['How to File a Grievance', 'What Evidence to Save'],
        'evidence': ['What Evidence to Save'],
        'open time': ['Open Time & Trip Pickup'],
        'trip trade': ['Open Time & Trip Pickup'],
        'pickup': ['Open Time & Trip Pickup'],
    }

    matched_cards = set()
    for keyword, cards in qrc_matches.items():
        if keyword in question_lower:
            matched_cards.update(cards)

    if matched_cards:
        card_list = ', '.join(f'**{c}**' for c in list(matched_cards)[:3])
        suggestions.append(f"\n\n💡 **Related Quick Reference Cards:** {card_list} — available from the Quick Reference menu above.")

    # Suggest trying rephrased question
    suggestions.append("\n\n🔄 **Tip:** Try rephrasing your question with specific contract terms (e.g., \"Section 6\" or \"per diem\" or \"reserve reassignment\"). The search works best with exact contract language.")

    return ''.join(suggestions)

# ============================================================
# ANALYTICS DASHBOARD
# ============================================================
def _load_top_questions():
    """Load top 5 most asked questions via logger (Turso or local fallback)."""
    try:
        logger = init_logger()
        contract_id = st.session_state.get('selected_contract')
        return logger.get_top_questions(5, contract_id=contract_id)
    except Exception:
        return []

def render_analytics_dashboard():
    """Render simple public analytics — just top questions."""
    st.markdown("## 🔥 Most Asked Questions")
    st.caption("See what other pilots are asking about")
    
    top = _load_top_questions()
    
    if top:
        for i, (q_text, count) in enumerate(top, 1):
            label = f"**{i}.** {q_text}"
            if count > 1:
                label += f"  ·  *asked {count} times*"
            st.markdown(label)
    else:
        st.caption("No questions logged yet. Be the first to ask!")

# ============================================================
# SESSION STATE
# ============================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'selected_contract' not in st.session_state:
    st.session_state.selected_contract = None
if 'show_reference' not in st.session_state:
    st.session_state.show_reference = None
if 'show_analytics' not in st.session_state:
    st.session_state.show_analytics = False
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}
if 'pending_question' not in st.session_state:
    st.session_state.pending_question = None

# ============================================================
# LOGIN
# ============================================================
if not st.session_state.authenticated:
    st.markdown("")
    st.markdown("")
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("""
        <div style="text-align:center; margin-bottom:1.5rem;">
            <div style="font-size:2.5rem; margin-bottom:0.25rem;">✈️</div>
            <div style="font-size:1.5rem; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">AskTheContract</div>
            <div style="font-size:0.85rem; color:#64748b; margin-top:0.25rem;">Contract Language Search Engine for Pilots</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter access password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            if submitted:
                try:
                    correct_password = st.secrets["APP_PASSWORD"]
                except Exception:
                    correct_password = "nacpilot2026"
                if password == correct_password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Contact the developer for access.")

        st.caption("🔒 Beta access — authorized users only")

# ============================================================
# MAIN APP
# ============================================================
else:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.25rem;">
        <span style="font-size:1.4rem; font-weight:700; color:#0f172a; letter-spacing:-0.02em;">✈️ AskTheContract</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Search and retrieve exact contract language with page and section references.")

    # ---- SIDEBAR ----
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:1rem 0 0.5rem;">
            <div style="font-size:1.15rem; font-weight:700; color:#ffffff; letter-spacing:-0.02em;">✈️ AskTheContract</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        manager = init_contract_manager()
        available_contracts = manager.get_available_contracts()

        contract_options = {
            info['airline_name']: contract_id
            for contract_id, info in available_contracts.items()
        }

        selected_name = st.selectbox(
            "Airline",
            options=list(contract_options.keys())
        )
        selected_contract_id = contract_options[selected_name]

        if st.session_state.selected_contract != selected_contract_id:
            st.session_state.selected_contract = selected_contract_id
            st.session_state.conversation = []

        contract_info = manager.get_contract_info(selected_contract_id)
        airline_name = contract_info['airline_name']

        st.markdown("---")

        # FEATURE 1: Quick Reference Cards
        st.caption("QUICK REFERENCE")

        for card_name, card_data in QUICK_REFERENCE_CARDS.items():
            if st.button(f"{card_data['icon']} {card_name}", key=f"ref_{card_name}", use_container_width=True):
                st.session_state.show_reference = card_name
                st.session_state.show_analytics = False

        st.markdown("---")
        if st.button("🔥 Most Asked", use_container_width=True):
            st.session_state.show_analytics = not st.session_state.show_analytics
            st.session_state.show_reference = None
            st.rerun()
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.show_reference = None
            st.rerun()
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ---- MAIN CONTENT ----
    st.markdown(f"""
    <div style="padding:0.6rem 1rem; background:#f1f5f9; border-radius:8px; font-size:0.8rem; color:#475569; margin-bottom:1rem;">
        Limited to the {airline_name} Pilot Contract (JCBA). Does not reference FAA regulations, company manuals, or other policies.
    </div>
    """, unsafe_allow_html=True)

    # Show Quick Reference Card if selected
    if st.session_state.show_reference:
        import streamlit.components.v1 as components
        components.html("""<script>
            var main = window.parent.document.querySelector('section.main');
            if (main) main.scrollTo({top: 0, behavior: 'instant'});
        </script>""", height=0)
        card = QUICK_REFERENCE_CARDS[st.session_state.show_reference]
        st.markdown(card['content'])
        if st.button("✖ Close Reference Card"):
            st.session_state.show_reference = None
            st.rerun()
        st.write("---")

    # Show Analytics Dashboard if selected
    if st.session_state.show_analytics:
        render_analytics_dashboard()
        if st.button("✖ Close"):
            st.session_state.show_analytics = False
            st.rerun()
        st.write("---")

    # Question input
    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            "Ask a question about your contract:",
            placeholder="Example: What is the daily pay guarantee?"
        )
        submit_button = st.form_submit_button("Ask", type="primary")

    if submit_button and question:
        st.session_state.pending_question = question

    # ---- CONTRACT CHAPTERS (empty state) ----
    if not st.session_state.conversation and not st.session_state.show_reference and not st.session_state.show_analytics and not st.session_state.pending_question:
        st.markdown("")
        st.markdown("""
        <div style="text-align:center; color:#64748b; font-size:0.85rem; font-weight:500; margin-bottom:0.75rem;">
            Explore your contract by section:
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        for i, (section, title, q_text) in enumerate(CONTRACT_CHAPTERS):
            with col_a if i < len(CONTRACT_CHAPTERS) // 2 else col_b:
                if st.button(f"{section} – {title}", key=f"chapter_{i}", use_container_width=True):
                    st.session_state.pending_question = q_text
                    st.rerun()

    # ---- PROCESS QUESTION (from form OR starter button) ----
    active_question = st.session_state.pending_question
    st.session_state.pending_question = None

    if active_question:
        st.session_state.show_reference = None

        # Prominent staged search indicator — visible on mobile and desktop
        search_placeholder = st.empty()

        def show_progress_stage(emoji, title, subtitle=""):
            subtitle_html = f'<div style="font-size:0.82rem; color:#3b82f6; margin-top:0.25rem;">{subtitle}</div>' if subtitle else ""
            search_placeholder.markdown(f"""
            <div style="padding:1.25rem 1.5rem; background:#eff6ff; border:2px solid #bfdbfe; border-radius:12px; text-align:center; margin:1rem 0;">
                <div style="font-size:1.5rem; margin-bottom:0.4rem;">{emoji}</div>
                <div style="font-size:1rem; font-weight:600; color:#1e40af;">{title}</div>
                {subtitle_html}
            </div>
            """, unsafe_allow_html=True)

        # Stage 1: Loading contract data
        show_progress_stage("📂", "Loading contract data…")

        with st.spinner(""):
            chunks, embeddings = load_contract(st.session_state.selected_contract)
            openai_client, anthropic_client = init_clients()
            history = st.session_state.conversation if st.session_state.conversation else None

            # Stage 2: Searching relevant sections
            show_progress_stage("🔍", "Searching relevant sections…", "Matching your question to contract provisions")

            answer, status, response_time = ask_question(
                active_question, chunks, embeddings,
                openai_client, anthropic_client,
                st.session_state.selected_contract,
                airline_name, history
            )

        # Clear the search indicator once answer is ready
        search_placeholder.empty()

        category = classify_question(active_question)

        logger = init_logger()
        logger.log_question(
            question_text=active_question,
            answer_text=answer,
            status=status,
            contract_id=st.session_state.selected_contract,
            response_time=response_time,
            category=category
        )

        st.session_state.conversation.append({
            'question': active_question,
            'answer': answer,
            'status': status,
            'category': category,
            'response_time': round(response_time, 1)
        })

    # ---- CONVERSATION HISTORY (hidden when QRC or cache review is open) ----
    if st.session_state.conversation and not st.session_state.show_reference:
        st.markdown("---")

        for i, qa in enumerate(reversed(st.session_state.conversation)):
            q_num = len(st.session_state.conversation) - i

            # Question header
            st.markdown(f"""
            <div style="display:flex; align-items:flex-start; gap:0.5rem; margin-bottom:0.25rem;">
                <span style="background:#0f172a; color:#fff; font-size:0.7rem; font-weight:700; padding:0.15rem 0.5rem; border-radius:100px; letter-spacing:0.03em; margin-top:0.2rem; white-space:nowrap;">Q{q_num}</span>
                <span style="font-size:1rem; font-weight:600; color:#0f172a;">{qa['question']}</span>
            </div>
            """, unsafe_allow_html=True)

            # FEATURE 2: Canonical Question Label
            category = qa.get('category', classify_question(qa['question']))
            answer_text = qa.get('answer', '')
            provision_count = max(answer_text.count('CITE:') + answer_text.count('📍'), answer_text.count('📄'))
            provision_label = f"  •  📄 {provision_count} provision{'s' if provision_count != 1 else ''}" if provision_count > 0 else ""
            st.caption(f"📂 {category}  •  ⏱️ {qa.get('response_time', '?')}s{provision_label}")

            # Answer with status color
            if qa['status'] == 'CLEAR':
                st.success(qa['answer'])
            elif qa['status'] == 'AMBIGUOUS':
                st.warning(qa['answer'])
            else:
                st.info(qa['answer'])

            # Bottom row
            col1, col2, col3, col4 = st.columns([1, 1, 3, 1])

            # FEATURE 4: Answer Rating
            rating_key = f"rating_{q_num}"
            feedback_key = f"feedback_open_{q_num}"
            with col1:
                if st.button("👍", key=f"up_{q_num}"):
                    log_rating(qa['question'], "up", st.session_state.selected_contract)
                    st.session_state.ratings[rating_key] = "up"
            with col2:
                if st.button("👎", key=f"down_{q_num}"):
                    log_rating(qa['question'], "down", st.session_state.selected_contract)
                    try:
                        cache = get_semantic_cache()
                        cache.record_thumbs_down(qa['question'], st.session_state.selected_contract)
                    except Exception:
                        pass
                    st.session_state.ratings[rating_key] = "down"
                    st.session_state[feedback_key] = True
            with col3:
                if rating_key in st.session_state.ratings:
                    r = st.session_state.ratings[rating_key]
                    if r == "up":
                        st.caption("✅ Thanks for your feedback!")

            # Feedback form (shows after 👎)
            if st.session_state.get(feedback_key):
                st.markdown("""
                <div style="padding:0.75rem 1rem; background:#fef9e7; border:1px solid #f0d36e; border-radius:8px; margin:0.5rem 0;">
                    <span style="font-size:0.85rem; color:#6b5900; font-weight:600;">Thanks for flagging this — help us fix it</span>
                </div>
                """, unsafe_allow_html=True)
                pilot_comment = st.text_area(
                    "What's wrong with this answer? (optional)",
                    placeholder="e.g. Wrong section number, math is off, missing a provision...",
                    key=f"comment_{q_num}",
                    max_chars=500,
                    height=80
                )
                if st.button("Submit Feedback", key=f"submit_fb_{q_num}"):
                    if pilot_comment and pilot_comment.strip():
                        try:
                            cache = get_semantic_cache()
                            cache.save_feedback(qa['question'], st.session_state.selected_contract, pilot_comment)
                        except Exception:
                            pass
                    st.session_state[feedback_key] = False
                    st.session_state.ratings[rating_key] = "down_submitted"
                    st.rerun()
                if st.session_state.ratings.get(rating_key) != "down_submitted":
                    st.caption("You can also skip this — the 👎 alone helps us find problems.")

            if st.session_state.ratings.get(rating_key) == "down_submitted":
                st.caption("📝 Thanks — we'll review this answer. Your feedback helps every pilot.")

            # FEATURE 5: Copy / Export Answer
            copy_text = f"""Question: {qa['question']}
Category: {category}
Status: {qa['status']}

{qa['answer']}

---
Generated by AskTheContract | {airline_name} JCBA
This is not legal advice."""

            with st.expander("📋 Copy / Export Answer"):
                st.code(copy_text, language=None)
                st.caption("Select all text above → Ctrl+C (or Cmd+C on Mac)")

            st.markdown("---")

        # Back button — clears conversation and returns to chapter grid
        if st.button("← Back to Contract Sections", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.show_reference = None
            st.rerun()

    # ---- FOOTER ----
    st.markdown("""
    <div style="text-align:center; padding:1rem 0; font-size:0.75rem; color:#94a3b8;">
        AskTheContract · Exact contract language, not legal advice
    </div>
    """, unsafe_allow_html=True)
