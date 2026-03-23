import os
import re
import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate


# =============================
# ENV
# =============================
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# =============================
# CLEAN DOCUMENTS
# =============================
def clean_documents(docs):
    return [d for d in docs if (d.page_content or "").strip()]


# =============================
# DETECT FULL HEADER
# =============================
def detect_full_semester_key(query):
    q = query.lower()

    year_map = {
        "e1": "FIRST",
        "e2": "SECOND",
        "e3": "THIRD",
        "e4": "FOURTH",
    }

    year_match = re.search(r"e[1-4]", q)
    sem_match = re.search(r"semester\s*(i{1,3}|iv|v|vi{0,2}|vii|viii)", q)

    if year_match and sem_match:
        year_code = year_match.group(0)
        sem = sem_match.group(1).upper()
        year_word = year_map.get(year_code)

        if year_word:
            return f"{year_word} YEAR (E{year_code[-1]}) – SEMESTER {sem}"

    return None


# =============================
# BUILD VECTOR STORE
# =============================
def build_db(pdf_path, persist_dir, branch_name=None, doc_type="general"):

    if not os.path.exists(persist_dir):

        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        split_docs = []

        if doc_type == "syllabus":

            full_text = "\n".join(
                [(d.page_content or "").strip() for d in docs]
            ).strip()

            # Robust header pattern (no dash dependency)
            header_pattern = re.compile(
                r"(?im)(FIRST|SECOND|THIRD|FOURTH)\s+YEAR\s*\(E(\d)\).*?SEMESTER\s*[IVX]+"
            )

            matches = list(header_pattern.finditer(full_text))

            if matches:
                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

                    header_text = match.group(0).strip()
                    content = full_text[start:end].strip()

                    split_docs.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": os.path.basename(pdf_path),
                                "branch": branch_name,
                                "semester": header_text.upper(),
                                "type": "syllabus",
                            },
                        )
                    )

            # Safety fallback
            if not split_docs:
                split_docs = [
                    Document(
                        page_content=full_text,
                        metadata={
                            "source": os.path.basename(pdf_path),
                            "branch": branch_name,
                            "semester": "FULL",
                            "type": "syllabus",
                        },
                    )
                ]

        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=150,
            )
            split_docs = splitter.split_documents(docs)

            for doc in split_docs:
                doc.metadata["source"] = os.path.basename(pdf_path)
                doc.metadata["page"] = doc.metadata.get("page", 0)
                doc.metadata["type"] = doc_type

        split_docs = clean_documents(split_docs)

        # Final safety guard (prevents empty embedding crash)
        if not split_docs:
            split_docs = [
                Document(
                    page_content="No extractable content.",
                    metadata={
                        "source": os.path.basename(pdf_path),
                        "branch": branch_name,
                        "semester": "FULL",
                        "type": doc_type,
                    },
                )
            ]

        db = Chroma.from_documents(
            documents=split_docs,
            embedding=embeddings,
            persist_directory=persist_dir,
        )

    else:
        db = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
        )

    return db


# =============================
# LOAD DATABASES
# =============================
@st.cache_resource
def load_dbs():

    base_path = "app/rgukt_datasets"
    r22_path = os.path.join(base_path, "r22")

    dbs = {}

    dbs["rules"] = build_db(
        os.path.join(base_path, "rules.pdf"),
        "./db_rules",
        doc_type="rules",
    )

    dbs["about"] = build_db(
        os.path.join(base_path, "about_rgukt.pdf"),
        "./db_about",
        doc_type="about",
    )

    for file in os.listdir(r22_path):
        if file.endswith(".pdf"):
            branch_key = file.replace(".pdf", "").lower()

            dbs[branch_key] = build_db(
                os.path.join(r22_path, file),
                f"./db_{branch_key}",
                branch_name=branch_key.upper(),
                doc_type="syllabus",
            )

    return dbs


# =============================
# ROUTER
# =============================
def route_query(query, dbs):
    q = query.lower()
    for key in dbs.keys():
        if key in q:
            return dbs[key]
    return dbs["rules"]


# =============================
# PROMPT
# =============================
def get_prompt():
    system_prompt = """
You are an AI assistant for RGUKT.

- Answer ONLY using the provided context.
- Use bullet points.
- Maximum 12 bullets.
- Be concise.
- Do not repeat lines.

If not found, say:
"Relevant information not found in the provided documents."

Context:
{context}
"""
    return ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{input}")]
    )


# =============================
# CHAT UI
# =============================
def main():

    st.set_page_config(page_title="RguBot", page_icon="🤖")
    st.title("🤖 RguBot - RGUKT Academic Assistant")

    dbs = load_dbs()
    prompt_template = get_prompt()

    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model="llama-3.1-8b-instant",
        temperature=0,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask about syllabus, rules, etc..."):

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        selected_db = route_query(user_input, dbs)

        docs = selected_db.similarity_search(user_input, k=6)

        full_key = detect_full_semester_key(user_input)

        if full_key:
            filtered = [
                d for d in docs
                if full_key in d.metadata.get("semester", "")
            ]
            if filtered:
                docs = filtered

        if not docs:
            response_text = "Relevant information not found in the provided documents."
        else:
            context_text = "\n\n".join([doc.page_content for doc in docs])
            context_text = context_text[:5000]

            formatted_prompt = prompt_template.format_messages(
                context=context_text,
                input=user_input,
            )

            response = llm.invoke(formatted_prompt)
            response_text = response.content.strip()

        with st.chat_message("assistant"):
            st.markdown(response_text)

            if docs:
                st.markdown("### 📚 Sources")
                seen = set()
                for doc in docs:
                    label = doc.metadata.get("semester", "")
                    if label not in seen:
                        seen.add(label)
                        st.markdown(f"- {label}")

        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )


if __name__ == "__main__":
    main()
