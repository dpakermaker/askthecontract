import streamlit as st
import pickle
import numpy as np
from openai import OpenAI
from anthropic import Anthropic
import time
import sys
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

# Load API keys
@st.cache_resource
def load_api_keys():
    # Try to load from Streamlit secrets (cloud deployment)
    try:
        keys = {
            'openai': st.secrets["OPENAI_API_KEY"],
            'anthropic': st.secrets["ANTHROPIC_API_KEY"]
        }
        return keys
    except:
        # Fall back to local file (local development)
        keys = {}
        with open('api_key.txt', 'r') as f:
            for line in f:
                if 'OPENAI_API_KEY' in line:
                    keys['openai'] = line.strip().split('=')[1]
                if 'ANTHROPIC_API_KEY' in line:
                    keys['anthropic'] = line.strip().split('=')[1]
        return keys

# Initialize clients
@st.cache_resource
def init_clients():
    keys = load_api_keys()
    openai_client = OpenAI(api_key=keys['openai'])
    anthropic_client = Anthropic(api_key=keys['anthropic'])
    return openai_client, anthropic_client

# Initialize contract manager
@st.cache_resource
def init_contract_manager():
    return ContractManager()

# Initialize logger
@st.cache_resource
def init_logger():
    return ContractLogger()

# Load contract data
@st.cache_resource
def load_contract(contract_id):
    manager = init_contract_manager()
    chunks, embeddings = manager.load_contract_data(contract_id)
    return chunks, embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_contract(question, chunks, embeddings, openai_client, max_chunks=75):
    # Create question embedding
    response = openai_client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    question_embedding = response.data[0].embedding

    # Find similar chunks
    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))

    # Sort and get top chunks
    similarities.sort(reverse=True, key=lambda x: x[0])
    return [chunk for score, chunk in similarities[:max_chunks]]

def ask_question(question, chunks, embeddings, openai_client, anthropic_client, contract_id):
    start_time = time.time()

    # Search for relevant chunks
    relevant_chunks = search_contract(question, chunks, embeddings, openai_client)

    # Build context
    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # Create prompt
    prompt = f"""You are analyzing a complete pilot union contract.

CONTRACT SECTIONS:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Provide accurate information from the contract
2. Quote exact contract language
3. Include page and section citations
4. If ambiguous, mark as AMBIGUOUS and show both interpretations
5. If not found, say "The contract does not appear to address this"
6. Add disclaimer that this is information only, not legal advice

Format your answer with:
📄 CONTRACT LANGUAGE: [exact quotes]
📍 [Section, Page]
📝 EXPLANATION: [plain English]
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED]

Answer:"""
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = message.content[0].text
    response_time = time.time() - start_time

    # Determine status
    if '🔵 STATUS: CLEAR' in answer:
        status = 'CLEAR'
    elif '🔵 STATUS: AMBIGUOUS' in answer:
        status = 'AMBIGUOUS'
    else:
        status = 'NOT_ADDRESSED'

    return answer, status, response_time

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'selected_contract' not in st.session_state:
    st.session_state.selected_contract = None

# Simple authentication (beta version)
if not st.session_state.authenticated:
    st.title("✈️ AskTheContract - Beta Access")
    st.write("**AI-Powered Contract Q&A for Pilots**")

    password = st.text_input("Enter beta password:", type="password")

    if st.button("Login"):
        if password == "nacpilot2026":  # Simple password for beta
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Contact the developer for access.")

    st.info("🔒 This is a beta test version for Northern Air Cargo pilots.")

else:
    # Main app
    st.title("✈️ AskTheContract")
    st.caption("AI-Powered Contract Q&A System")

    # Sidebar
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

        # Load contract if changed
        if st.session_state.selected_contract != selected_contract_id:
            st.session_state.selected_contract = selected_contract_id
            st.session_state.conversation = []

        # Show contract info
        contract_info = manager.get_contract_info(selected_contract_id)
        st.info(f"""
        **{contract_info['airline_name']}**

        📄 Pages: {contract_info['total_pages']}

        📅 Version: {contract_info['contract_version']}

        ✈️ Aircraft: {contract_info.get('b737_cola', 'N/A')}
        """)

        if st.button("Clear Conversation"):
            st.session_state.conversation = []
            st.rerun()

        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    # Main content
    st.write("---")

    # Question input in a form (clears after submit)
    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            "Ask a question about your contract:",
            placeholder="Example: What is the daily pay guarantee?"
        )
        submit_button = st.form_submit_button("Ask", type="primary")

    if submit_button and question:
        with st.spinner("Searching contract and generating answer..."):
            # Load contract data
            chunks, embeddings = load_contract(st.session_state.selected_contract)

            # Initialize clients
            openai_client, anthropic_client = init_clients()

            # Get answer
            answer, status, response_time = ask_question(
                question, chunks, embeddings,
                openai_client, anthropic_client,
                st.session_state.selected_contract
            )

            # Log the question
            logger = init_logger()
            logger.log_question(
                question_text=question,
                answer_text=answer,
                status=status,
                contract_id=st.session_state.selected_contract,
                response_time=response_time
            )

            # Add to conversation
            st.session_state.conversation.append({
                'question': question,
                'answer': answer,
                'status': status
            })

    # Display conversation
    if st.session_state.conversation:
        st.write("---")
        st.subheader("Conversation History")

        for i, qa in enumerate(reversed(st.session_state.conversation)):
            with st.container():
                st.write(f"**Q{len(st.session_state.conversation) - i}:** {qa['question']}")

                # Color code based on status
                if qa['status'] == 'CLEAR':
                    st.success(qa['answer'])
                elif qa['status'] == 'AMBIGUOUS':
                    st.warning(qa['answer'])
                else:
                    st.info(qa['answer'])

                st.write("---")

    # Footer
    st.caption("⚠️ **Disclaimer:** This tool provides contract information only. It is not legal advice. Verify all answers against the actual contract and consult your union representative for guidance on disputes.")