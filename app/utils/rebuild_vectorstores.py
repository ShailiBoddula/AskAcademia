import logging
import os
from typing import List
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Shared embeddings instance (created once)
EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

DEPARTMENTS = {
    "CSE": "app/rgukt_datasets/r22/cse.pdf",
    "ECE": "app/rgukt_datasets/r22/ece.pdf",
    "EEE": "app/rgukt_datasets/r22/eee.pdf",
    "MECH": "app/rgukt_datasets/r22/mech.pdf",
    "MME": "app/rgukt_datasets/r22/mme.pdf",
    "CIVIL": "app/rgukt_datasets/r22/civil.pdf",
    "RULES": "app/rgukt_datasets/rules.pdf",
}

DB_PATHS = {
    "CSE": "db_cse",
    "ECE": "db_ece",
    "EEE": "db_eee",
    "MECH": "db_mech",
    "MME": "db_mme",
    "CIVIL": "db_civil",
    "RULES": "db_rules",
}


def load_department_pdfs(file_path: str) -> List[Document]:
    """Load a single department PDF."""
    documents: List[Document] = []

    if not os.path.exists(file_path):
        logger.warning(f"PDF not found: {file_path}")
        return documents

    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        department = os.path.basename(file_path).replace(".pdf", "")

        for doc in docs:
            doc.metadata["source"] = os.path.basename(file_path)
            doc.metadata["department"] = department.upper()

        documents.extend(docs)
        logger.info(f"Loaded {len(docs)} pages from {file_path}")

    except Exception as e:
        logger.error(f"Failed to load PDF {file_path}: {str(e)}")

    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """Split documents into chunks using RecursiveCharacterTextSplitter."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    return text_splitter.split_documents(documents)


def build_vectorstore(documents: List[Document], persist_directory: str) -> None:
    """Build and persist Chroma vector store (fresh each time)."""
    if not documents:
        logger.warning(f"No documents to build vectorstore for {persist_directory}")
        return

    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        logger.info(f"Cleared existing database: {persist_directory}")

    try:
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=EMBEDDINGS,
            persist_directory=persist_directory
        )
        logger.info(f"Persisted {len(documents)} chunks to {persist_directory}")
    except Exception as e:
        logger.error(f"Failed to build vectorstore for {persist_directory}: {str(e)}")


def rebuild_all_vectorstores() -> None:
    """Rebuild vector stores for all departments."""
    logger.info("Starting full vectorstore rebuild...")

    for dept, folder in DEPARTMENTS.items():
        try:
            logger.info(f"Processing department: {dept}")
            raw_docs = load_department_pdfs(folder)

            if not raw_docs:
                logger.warning(f"No PDFs found for {dept}. Skipping.")
                continue

            chunks = split_documents(raw_docs)
            logger.info(f"Created {len(chunks)} chunks for {dept}")

            db_path = DB_PATHS[dept]
            build_vectorstore(chunks, db_path)

        except Exception as e:
            logger.error(f"Failed to process {dept}: {str(e)}. Continuing with next department...")

    logger.info("Vectorstore rebuild completed.")


if __name__ == "__main__":
    rebuild_all_vectorstores()
