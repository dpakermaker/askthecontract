import streamlit as st
import pickle
import numpy as np
from openai import OpenAI
from anthropic import Anthropic
import time
import sys
import threading
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from contract_manager import ContractManager
from contract_logger import ContractLogger

# Page config
st.set_page_config(
    page_title="AskTheContract",
    page_icon="✈️",
    layout="wide"
)

# ============================================================
# SEMANTIC SIMILARITY CACHE
# ============================================================
class SemanticCache:
    SIMILARITY_THRESHOLD = 0.96
    MAX_ENTRIES = 500

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}

    def lookup(self, embedding, contract_id):
        with self._lock:
            entries = self._entries.get(contract_id, [])
            for cached_emb, cached_q, cached_answer, cached_status, cached_time in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD:
                    return cached_answer, cached_status, cached_time
        return None

    def store(self, embedding, question, answer, status, response_time, contract_id):
        with self._lock:
            if contract_id not in self._entries:
                self._entries[contract_id] = []
            entries = self._entries[contract_id]
            if len(entries) >= self.MAX_ENTRIES:
                entries.pop(0)
            entries.append((embedding, question, answer, status, response_time))

    def clear(self, contract_id=None):
        with self._lock:
            if contract_id:
                self._entries.pop(contract_id, None)
            else:
                self._entries = {}

@st.cache_resource
def get_semantic_cache():
    return SemanticCache()

# ============================================================
# STANDARD INIT FUNCTIONS
# ============================================================

@st.cache_resource
def load_api_keys():
    try:
        keys = {
            'openai': st.secrets["OPENAI_API_KEY"],
            'anthropic': st.secrets["ANTHROPIC_API_KEY"]
        }
        return keys
    except:
        keys = {}
        with open('api_key.txt', 'r') as f:
            for line in f:
                if 'OPENAI_API_KEY' in line:
                    keys['openai'] = line.strip().split('=')[1]
                if 'ANTHROPIC_API_KEY' in line:
                    keys['anthropic'] = line.strip().split('=')[1]
        return keys

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

@st.cache_data(ttl=86400, show_spinner=False)
def get_embedding_cached(question_text, _openai_client):
    response = _openai_client.embeddings.create(
        input=question_text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# ============================================================
# FORCE-INCLUDE CHUNKS
# When certain topics are detected, always include chunks
# containing critical contract language regardless of
# embedding similarity score. This ensures key provisions
# are never missed due to how the question is worded.
# ============================================================

# Phrases that MUST be in the context when topic is detected
FORCE_INCLUDE_RULES = {
    'days_off': {
        'trigger_keywords': ['day off', 'days off', 'rest period', 'week off', 'time off', 'duty free', 'one day per week', 'day per week', 'weekly day'],
        'must_include_phrases': [
            'regular line shall be scheduled with at least one (1) day off in any seven',
            'composite line shall be scheduled with at least one (1) scheduled day off in any seven',
            'shall receive at least one (1) twenty-four (24) hour rest period free from all duty within any seven',
            'schedule the pilot for one (1) day off in every seven (7) days',
            'minimum scheduled days off in all constructed initial lines shall be thirteen',
            'shall have at least two (2) separate periods of at least three (3) consecutive days off',
            'scheduled to have a minimum of one (1) day off during every seven (7) consecutive days of training',
            'minimum rest requirements for a pilot who is awarded a domicile flex line',
        ]
    },
    'pay': {
        'trigger_keywords': ['pay', 'rate', 'hourly', 'salary', 'wage', 'compensation', 'dpg', 'daily pay guarantee', 'duty rig', 'trip rig', 'pch', 'make per hour'],
        'must_include_phrases': [
            'daily pay guarantee',
            'one (1) pch for every two (2) hours',
            'trip rig',
            'open time premium',
            'junior assignment premium',
            'monthly pay guarantee',
        ]
    }
}

def find_force_include_chunks(question_lower, all_chunks):
    """Find chunks that MUST be included based on question topic."""
    forced = []
    for rule_name, rule in FORCE_INCLUDE_RULES.items():
        # Check if any trigger keyword matches
        if any(kw in question_lower for kw in rule['trigger_keywords']):
            # Find chunks containing the must-include phrases
            for chunk in all_chunks:
                chunk_text_lower = chunk['text'].lower()
                for phrase in rule['must_include_phrases']:
                    if phrase in chunk_text_lower:
                        if chunk not in forced:
                            forced.append(chunk)
                        break  # One match per chunk is enough
    return forced

def search_contract(question, chunks, embeddings, openai_client, max_chunks=75):
    question_embedding = get_embedding_cached(question, openai_client)
    question_lower = question.lower()

    # Step 1: Find force-include chunks for this question topic
    forced_chunks = find_force_include_chunks(question_lower, chunks)

    # Step 2: Normal embedding search
    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))

    similarities.sort(reverse=True, key=lambda x: x[0])
    embedding_chunks = [chunk for score, chunk in similarities[:max_chunks]]

    # Step 3: Merge - forced chunks first, then fill remaining from embedding results
    # Deduplicate by chunk id
    seen_ids = set()
    merged = []

    # Add forced chunks first (these are critical and must always be present)
    for chunk in forced_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)

    # Fill remaining slots with embedding results
    for chunk in embedding_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_chunks:
                break

    return merged

# ============================================================
# API CALL (only runs on cache miss)
# ============================================================
def _ask_question_api(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name):
    start_time = time.time()

    pay_keywords = ['pay', 'rate', 'hourly', 'salary', 'wage', 'compensation', 'earning', 'make per hour', 'dpg', 'scale', 'duty rig', 'trip rig', 'pch']
    scheduling_keywords = ['day off', 'days off', 'rest period', 'rest requirement', 'schedule', 'line construction', 'composite line', 'regular line', 'reserve line', 'bid line', 'workday', 'work day', 'consecutive days', 'week off', 'time off', 'duty free']

    question_lower = question.lower()
    is_pay_question = any(keyword in question_lower for keyword in pay_keywords)
    is_scheduling_question = any(keyword in question_lower for keyword in scheduling_keywords)

    if is_pay_question or is_scheduling_question:
        max_chunks = 100
    else:
        max_chunks = 75

    relevant_chunks = search_contract(question, chunks, embeddings, openai_client, max_chunks=max_chunks)

    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA). Your role is to provide accurate, unbiased contract analysis based solely on the contract language provided to you.

SCOPE LIMITATION:
This tool ONLY searches the {airline_name} pilot union contract (JCBA). It does NOT have access to:
- FAA regulations or Federal Aviation Regulations (FARs)
- Company Operations Manuals or Standard Operating Procedures (SOPs)
- Company policies, memos, or bulletins
- Other labor agreements or side letters not included in the JCBA
- State or federal employment laws
If a question appears to be about any of these sources, clearly state: "This tool only searches the {airline_name} pilot contract (JCBA) and cannot answer questions about FAA regulations, company manuals, or other policies outside the contract."

CORE PRINCIPLES:
1. Quote exact contract language - always use the precise wording from the contract
2. Cite every quote with section number and page number
3. Never interpret beyond what the contract explicitly states
4. Never assume provisions exist that are not in the provided text
5. Never use directive language like "you get" or "company owes" - instead say "the contract states" or "per the contract language"
6. Always acknowledge when the contract is silent on a topic
7. When multiple provisions may apply, cite all of them

ANALYSIS RULES:
- Read ALL provided contract sections before forming your answer
- Look for provisions that may apply from different sections (pay, scheduling, reserve, hours of service, etc.)
- Check for defined terms - many words have specific contract definitions
- Pay attention to qualifiers like "shall", "may", "except", "unless", "notwithstanding", "provided"
- Note the difference between "scheduled" vs "actual" and "assigned" vs "awarded"
- Distinguish between different pilot categories: Regular Line holders, Reserve pilots (R-1, R-2, R-3, R-4), Composite Line holders, TDY pilots, Domicile Flex Line holders
- Distinguish between different types of assignments: Trip Pairings, Reserve Assignments, Company-Directed Assignments, Training, Deadhead
- When a provision applies only to specific categories, state which categories clearly

PAY QUESTION RULES:
When the question involves pay or compensation, you MUST:
- Identify the pilot's position (Captain or First Officer) and longevity year if provided
- Calculate all potentially applicable pay provisions including:
  * Daily Pay Guarantee (DPG): 3.82 PCH multiplied by hourly rate
  * Duty Rig: total duty hours divided by 2, multiplied by hourly rate
  * Trip Rig (TAFD): total TAFD hours divided by 4.9, multiplied by hourly rate
  * Scheduled PCH if provided in the scenario
  * Overtime Premium: PCH multiplied by hourly rate multiplied by 1.5
- Show all math step by step
- Quote the contract language that defines each calculation
- State which calculation the contract says applies, or if the contract does not specify

SCHEDULING AND REST QUESTION RULES:
When the question involves days off, rest periods, scheduling, or duty limits:
- Check provisions across Section 13 (Hours of Service), Section 14 (Scheduling), and Section 15 (Reserve Duty)
- Note that different line types (Regular, Composite, Reserve, TDY, Domicile Flex) have different rules
- Cite the specific line type or duty status each provision applies to
- Note minimum days off requirements for monthly line construction
- Note rest period requirements between duty assignments
- Distinguish between "Day Off" (defined term) and "Rest Period" (defined term)

STATUS DETERMINATION:
After your analysis, assign one of these statuses:

CLEAR - Use when:
- The contract explicitly and unambiguously answers the question
- All terms in the relevant provisions are defined
- There are no conflicting provisions
- The contract specifies exactly which calculation or rule applies

AMBIGUOUS - Use when:
- The contract uses undefined terms in the relevant provisions
- Multiple provisions could apply and the contract does not specify which one
- Provisions appear to conflict with each other
- The contract language is open to more than one reasonable interpretation
- The contract addresses the topic partially but not completely

NOT ADDRESSED - Use when:
- The contract does not contain any language relevant to the question
- The provided sections do not cover the topic asked about

RESPONSE FORMAT:
Always structure your response exactly as follows:

📄 CONTRACT LANGUAGE: [Quote exact contract text with quotation marks]
📍 [Section number, Page number]

(Repeat for each relevant provision found)

📝 EXPLANATION: [Plain English explanation of what the contract language means, how provisions interact, and what the answer to the question is based solely on the contract text]

🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence justification for the status]

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

IMPORTANT REMINDERS:
- If you cannot find relevant language in the provided sections, say so clearly
- Do not speculate about what the contract "probably" means or what "common practice" is
- Do not reference external laws, FARs, or regulations unless the contract itself references them
- Every claim you make must be traceable to a specific quoted provision
- When provisions from multiple sections are relevant, cite all of them
- Be thorough but concise - pilots need clear, actionable information"""

    user_content = f"""CONTRACT SECTIONS:
{context}

QUESTION: {question}

Answer:"""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": user_content}]
    )

    answer = message.content[0].text
    response_time = time.time() - start_time

    if '🔵 STATUS: CLEAR' in answer:
        status = 'CLEAR'
    elif '🔵 STATUS: AMBIGUOUS' in answer:
        status = 'AMBIGUOUS'
    else:
        status = 'NOT_ADDRESSED'

    return answer, status, response_time

# ============================================================
# MAIN ENTRY POINT
# ============================================================
def ask_question(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name):
    normalized = question.strip().lower()

    question_embedding = get_embedding_cached(normalized, openai_client)

    semantic_cache = get_semantic_cache()
    cached_result = semantic_cache.lookup(question_embedding, contract_id)
    if cached_result is not None:
        return cached_result

    answer, status, response_time = _ask_question_api(
        normalized, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name
    )

    semantic_cache.store(question_embedding, normalized, answer, status, response_time, contract_id)

    return answer, status, response_time

# ============================================================
# SESSION STATE
# ============================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'selected_contract' not in st.session_state:
    st.session_state.selected_contract = None

if not st.session_state.authenticated:
    st.title("✈️ AskTheContract - Beta Access")
    st.write("**AI-Powered Contract Q&A for Pilots**")

    password = st.text_input("Enter beta password:", type="password")

    if st.button("Login"):
        if password == "nacpilot2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Contact the developer for access.")

    st.info("🔒 This is a beta test version.")

else:
    st.title("✈️ AskTheContract")
    st.caption("AI-Powered Contract Q&A System")

    with st.sidebar:
        st.header("Contract Selection")

        manager = init_contract_manager()
        available_contracts = manager.get_available_contracts()

        contract_options = {
            info['airline_name']: contract_id
            for contract_id, info in available_contracts.items()
        }

        selected_name = st.selectbox(
            "Select your airline:",
            options=list(contract_options.keys())
        )

        selected_contract_id = contract_options[selected_name]

        if st.session_state.selected_contract != selected_contract_id:
            st.session_state.selected_contract = selected_contract_id
            st.session_state.conversation = []

        contract_info = manager.get_contract_info(selected_contract_id)
        airline_name = contract_info['airline_name']

        st.info(f"""
        **{airline_name}**

        📄 Pages: {contract_info['total_pages']}

        📅 Version: {contract_info['contract_version']}
        """)

        if st.button("Clear Conversation"):
            st.session_state.conversation = []
            st.rerun()

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    st.write("---")

    st.info(f"📋 This tool searches **only** the **{airline_name} Pilot Contract (JCBA)**. It does not cover FAA regulations (FARs), Company Operations Manuals, or other policies.")

    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            "Ask a question about your contract:",
            placeholder="Example: What is the daily pay guarantee?"
        )
        submit_button = st.form_submit_button("Ask", type="primary")

    if submit_button and question:
        with st.spinner("Searching contract and generating answer..."):
            chunks, embeddings = load_contract(st.session_state.selected_contract)
            openai_client, anthropic_client = init_clients()

            answer, status, response_time = ask_question(
                question, chunks, embeddings,
                openai_client, anthropic_client,
                st.session_state.selected_contract,
                airline_name
            )

            logger = init_logger()
            logger.log_question(
                question_text=question,
                answer_text=answer,
                status=status,
                contract_id=st.session_state.selected_contract,
                response_time=response_time
            )

            st.session_state.conversation.append({
                'question': question,
                'answer': answer,
                'status': status
            })

    if st.session_state.conversation:
        st.write("---")
        st.subheader("Conversation History")

        for i, qa in enumerate(reversed(st.session_state.conversation)):
            with st.container():
                st.write(f"**Q{len(st.session_state.conversation) - i}:** {qa['question']}")

                if qa['status'] == 'CLEAR':
                    st.success(qa['answer'])
                elif qa['status'] == 'AMBIGUOUS':
                    st.warning(qa['answer'])
                else:
                    st.info(qa['answer'])

                st.write("---")

    st.caption("⚠️ **Disclaimer:** This tool searches only the pilot union contract (JCBA). It does not cover FAA regulations, company manuals, or other policies. This is not legal advice. Verify all answers against the actual contract and consult your union representative for guidance on disputes.")
