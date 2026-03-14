import streamlit as st
import os
import pandas as pd
import subprocess
import json
import time
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

st.set_page_config(page_title="USC Venue Explorer", page_icon="🏋️", layout="wide")

DATA_PATH = "output/data.csv"
EMBEDDINGS_PATH = "output/embeddings.json"

st.title("🏋️ USC Venue Explorer")

@st.cache_resource
def load_rag_chain():
    # If using pre-computed embeddings, FAISS/Langchain expects full indexing. 
    # For a simple setup without heavy pre-caching setup complexity, we will lazily load texts and embed via API into a rapid FAISS index.
    # A real production app might load the `embeddings.json` directly into a custom vectorstore, but since we are working with rapid RAG here:
    
    if not os.path.exists(DATA_PATH):
        return None
        
    df = pd.read_csv(DATA_PATH)
    if "Combined_Text" not in df.columns:
        return None
        
    documents = [Document(page_content=str(row), metadata={"source": idx}) for idx, row in df["Combined_Text"].items()]
    
    # Needs OPENAI_API_KEY from .env
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(documents, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_template("""You are an assistant for answering questions about Urban Sports Club venues and classes.
    Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know. 
    Keep the answer concise and formatting clear. Structure schedules logically.
    Context: {context}
    Question: {input}
    Answer:""")
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, document_chain)

# --- Sidebar Controls ---
st.sidebar.header("📊 Dataset Overview")

data_exists = os.path.exists(DATA_PATH)

if not data_exists:
    st.sidebar.warning("⚠️ No Venue Data Discovered. Run Crawler First!")
    st.sidebar.write("The `output/data.csv` file is missing. The Chat requires this file to formulate answers.")
else:
    try:
        df = pd.read_csv(DATA_PATH)
        st.sidebar.success("✅ Dataset Loaded successfully")
        st.sidebar.metric("Total Classes", len(df))
        if "Venue Name" in df.columns:
            st.sidebar.metric("Unique Venues", df["Venue Name"].nunique())
            
    except Exception as e:
        st.sidebar.error(f"Error reading dataset: {e}")

st.sidebar.divider()

@st.dialog("🚀 Start New Crawl")
def crawl_dialog():
    st.write("Crawl new Urban Sports Club schedule data. This process overwrites existing CSV output.")
    
    city = st.selectbox("Select City", [
        "Köln", "Berlin", "München", "Hamburg", "Frankfurt",
        "Stuttgart", "Düsseldorf", "Leipzig", "Hannover", "Nürnberg"
    ])
    
    days = st.number_input("Days to Fetch (Schedule horizon)", min_value=1, max_value=30, value=7, step=1)
    
    if st.button("Start Crawler", use_container_width=True, type="primary"):
        with st.spinner("Executing Crawler Pipeline... This can take a moment."):
            cmd = [
                ".venv/bin/python", "main.py", 
                "--city", city,
                "--days", str(days)
            ]
            
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                st.success("Crawl completed successfully!")
                
                with st.expander("Show Logs"):
                    st.code(res.stdout)
                
                time.sleep(2)
                st.rerun()
            except subprocess.CalledProcessError as e:
                st.error("Crawler Failed!")
                st.code(e.stderr)

if st.sidebar.button("⚙️ Recrawl Data", use_container_width=True):
    crawl_dialog()

# --- Main Chat UI ---

st.write("Interact directly with your scheduled courses catalog.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("E.g., Which yoga classes are available tomorrow evening in Köln?"):
    if not data_exists:
        st.error("Please run the crawler first to populate data before chatting.")
    else:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        chain = load_rag_chain()
        if not chain:
            st.error("Failed to initialize RAG pipeline. Verify DATA_PATH and OPENAI_API_KEY.")
        else:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing schedule..."):
                    try:
                        response = chain.invoke({"input": prompt})
                        answer = response["answer"]
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        st.error(f"Chat error generated: {e}")
