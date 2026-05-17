# Replace the entire content of app/tools/notice_tool.py with this:

import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import httpx
from langchain_core.tools import tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
MAX_PAGES = 5
TIMEOUT = 15.0


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def truncate_text(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def fetch_html(url: str) -> Optional[str]:
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

def parse_notice(element: BeautifulSoup) -> Optional[Dict[str, str]]:
    """Parse a single notice from <li> or card element."""
    try:
        a_tag = element.find("a")
        full_text = clean_text(a_tag.get_text()) if a_tag else ""

        # Skip junk
        junk = ["click here", "download", "notice attachment", "next", "previous"]
        if any(j in full_text.lower() for j in junk) or len(full_text) < 15:
            return None

        # Date + Title
        if ":" in full_text:
            date, title = full_text.split(":", 1)
            date = clean_text(date)
            title = clean_text(title)
        else:
            date = "Date not available"
            title = full_text

        # Body
        pre = element.find("pre")
        body = clean_text(pre.get_text()) if pre else "Notice details available on RGUKT portal."

        # PDF Link - Improved detection
        pdf_link = ""
        
        # Method 1: Link containing "Download"
        download_link = element.find("a", string=lambda t: t and "download" in str(t).lower())
        if download_link and download_link.get("href"):
            href = download_link["href"]
            pdf_link = href if href.startswith("http") else f"https://hub.rgukt.ac.in{href}"
        
        # Method 2: Any .pdf link (fallback)
        if not pdf_link:
            pdf_a = element.find("a", href=lambda x: x and ".pdf" in x.lower())
            if pdf_a and pdf_a.get("href"):
                href = pdf_a["href"]
                pdf_link = href if href.startswith("http") else f"https://hub.rgukt.ac.in{href}"

        return {
            "title": truncate_text(title, 150),
            "date": date,
            "body": truncate_text(body, 150),
            "pdf_link": pdf_link
        }
    except Exception as e:
        logger.warning(f"Failed to parse notice: {e}")
        return None

        # Split date and title
        if ":" in full_text:
            date, title = full_text.split(":", 1)
            date = clean_text(date)
            title = clean_text(title)
        else:
            date = "Date not available"
            title = full_text

        # Body
        pre = element.find("pre")
        body = clean_text(pre.get_text()) if pre else "Notice details available on RGUKT portal."

        # PDF Link
        pdf_link = ""
        download = element.find("a", string=lambda t: t and "Download" in str(t))
        if download and download.get("href"):
            href = download["href"]
            pdf_link = href if href.startswith("http") else f"https://hub.rgukt.ac.in{href}"
        else:
            pdf_a = element.find("a", href=lambda x: x and ".pdf" in x.lower())
            if pdf_a and pdf_a.get("href"):
                href = pdf_a["href"]
                pdf_link = href if href.startswith("http") else f"https://hub.rgukt.ac.in{href}"

        return {
            "title": truncate_text(title, 150),
            "date": date,
            "body": truncate_text(body, 150)
        }
    except Exception as e:
        logger.warning(f"Failed to parse notice: {e}")
        return None


def scrape_notices_page(page: int = 1) -> List[Dict[str, str]]:
    """Scrape notices with deduplication and junk filtering."""
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    logger.info(f"Scraping: {url}")

    html = fetch_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    notices = []
    seen = set()

    # Junk titles to skip
    junk_titles = {"click here", "download", "next", "previous", "login", "home"}

    for item in soup.find_all(["li", "div"]):
        if not item.find("pre"):
            continue

        notice = parse_notice(item)
        if not notice:
            continue

        title_lower = notice["title"].lower()
        if title_lower in junk_titles or len(title_lower) < 10:
            continue

        # Deduplication key
        key = (notice["title"], notice["date"])
        if key in seen:
            continue
        seen.add(key)

        notices.append(notice)

    logger.info(f"Page {page}: found {len(notices)} notices")
    return notices

@tool
def fetch_rgukt_notices(query: str = "", pages: int = 1) -> Dict[str, Any]:
    """
    Fetch latest notices from RGUKT Hub, filtered by the user's query when possible.

    Args:
        query: The user's original question or keywords (e.g., "scholarship", "E1 branch", "exam results", "SC category")
        pages: Number of pages to scrape (1-5). Default is 1.

    Returns:
        Dictionary containing filtered list of notices.
    """
    try:
        pages = max(1, min(int(pages), MAX_PAGES))
    except:
        pages = 1

    all_notices = []
    for p in range(1, pages + 1):
        all_notices.extend(scrape_notices_page(p))

    if not all_notices:
        return {
            "notices": [],
            "message": "Could not fetch live notices. Please check https://hub.rgukt.ac.in/hub/notice/index directly."
        }

    # Filter notices based on query
    if query:
        query_lower = query.lower()

        # Special handling for recruitment/placement queries
        recruitment_keywords = ["recruitment", "placement", "job drive", "campus drive", "shortlisted", "interview", "written examination", "recruitment drive"]
        is_recruitment_query = any(kw in query_lower for kw in recruitment_keywords)

        if is_recruitment_query:
            filtered = [
                n for n in all_notices
                if any(kw in n.get("title", "").lower() or kw in n.get("body", "").lower() 
                       for kw in recruitment_keywords)
            ]
        else:
            filtered = [
                n for n in all_notices
                if query_lower in n.get("title", "").lower() or
                   query_lower in n.get("body", "").lower()
            ]

        all_notices = filtered if filtered else all_notices

    # Deduplicate + limit to 5 (only recruitment notices)
    seen = set()
    final = []
    for n in all_notices:
        if n["title"] not in seen:
            seen.add(n["title"])
            final.append(n)
        if len(final) >= 5:
            break

    logger.info(f"Returning {len(final)} recruitment notices")
    return {"notices": final}