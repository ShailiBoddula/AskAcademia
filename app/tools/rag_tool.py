import logging
import os
from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        logger.info("Loading HuggingFace embeddings (first request)...")
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings

# Module-level retrievers for all departments (loaded once)
DB_PATHS = {
    "CSE": "./db_cse",
    "ECE": "./db_ece",
    "EEE": "./db_eee",
    "MECH": "./db_mech",
    "MME": "./db_mme",
    "CIVIL": "./db_civil",
    "RULES": "./db_rules",
}

retrievers: Dict[str, Any] = {}
_retrievers_loaded = False

def get_retrievers():
    global retrievers, _retrievers_loaded
    if not _retrievers_loaded:
        logger.info("Loading ChromaDB retrievers (first request)...")
        embeddings = get_embeddings()
        for dept, path in DB_PATHS.items():
            if os.path.exists(path):
                db = Chroma(persist_directory=path, embedding_function=embeddings)
                retrievers[dept] = db.as_retriever(search_kwargs={"k": 4})
                logger.info(f"Loaded retriever for {dept}")
            else:
                logger.warning(f"DB not found for {dept}: {path}")
        _retrievers_loaded = True
    return retrievers


def determine_department(query: str) -> str:
    """Detect most relevant department from query keywords."""
    query_lower = query.lower()
    
    # CSE
    if any(kw in query_lower for kw in ["cse", "computer science", "cs", "programming", "data structure", "algorithm", "software", "database"]):
        return "CSE"
    
    # ECE
    if any(kw in query_lower for kw in ["ece", "electronics", "communication", "vlsi", "embedded", "microprocessor", "digital electronics", "analog", "signal processing", "optical"]):
        return "ECE"
    
    # EEE
    if any(kw in query_lower for kw in ["eee", "electrical", "power", "circuit", "machines", "control systems", "power systems", "electrical engineering", "transformer"]):
        return "EEE"
    
    # MECH
    if any(kw in query_lower for kw in ["mech", "mechanical", "thermodynamics", "fluid mechanics", "heat transfer", "manufacturing", "machine design", "mechanical engineering", "machine", "automobile"]):
        return "MECH"
    
    # MME
    if any(kw in query_lower for kw in ["mme", "metallurgy", "materials", "material science"]):
        return "MME"
    
    # CIVIL
    if any(kw in query_lower for kw in ["civil", "structural", "concrete", "geotechnical", "transportation"]):
        return "CIVIL"
    
    # Default to RULES
    return "RULES"


def truncate_text(text: str, limit: int = 200) -> str:
    """Cleanly truncate text for previews."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


@tool
def search_rgukt_documents(query: str) -> Dict[str, Any]:
    """
    Retrieve relevant academic information from the correct RGUKT department database.
    
    Args:
        query: Student question about academic regulations, department subjects, or handbook content
        
    Returns:
        Structured dictionary with selected department, answer and source citations
    """
    logger.info(f"Executing search_rgukt_documents with query: {query[:100]}...")
    
    try:
        department = determine_department(query)
        retriever = get_retrievers().get(department, get_retrievers().get("RULES"))
        
        if retriever is None:
            logger.error(f"No retriever available for department: {department}")
            return {
                "department": department,
                "answer": "No database is currently available for this department.",
                "sources": []
            }
        
        docs = retriever.invoke(query)
        
        if not docs:
            logger.warning(f"No documents found in {department} database")
            return {
                "department": department,
                "answer": "I couldn't find relevant information in the selected database. Please try rephrasing your question.",
                "sources": []
            }
        
        combined_content = "\n\n".join(
            [truncate_text(doc.page_content, 500) for doc in docs]
        )
        
        sources: List[Dict[str, Any]] = []
        for doc in docs:
            metadata = doc.metadata
            sources.append({
                "file": metadata.get("source", "RGUKT_Document.pdf"),
                "page": metadata.get("page") or metadata.get("page_number", 0),
                "preview": truncate_text(doc.page_content, 200)
            })
        
        logger.info(f"Retrieved {len(docs)} documents from {department} database")
        
        return {
            "department": department.upper() if department != "rules" else "RULES",
            "answer": combined_content,
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Error in search_rgukt_documents: {str(e)}")
        return {
            "department": "RULES",
            "answer": "An error occurred while retrieving information. Please try again later.",
            "sources": []
        }
