"""Step 1 of indexing: turn every file into clean text + metadata."""
import csv
import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


def office_from_name(path: Path) -> str:
    name = path.name.lower()
    if "india" in name:
        return "india"
    if "germany" in name:
        return "germany"
    return "all"


def load_pdf(path: Path) -> list[dict]:
    """One record per page. Removes the repeating header/footer lines."""
    records = []
    for page_no, page in enumerate(PdfReader(path).pages, start=1):
        text = page.extract_text() or ""
        lines = [
            ln for ln in text.splitlines()
            if not ln.startswith("Nimbus Corp Employee Handbook - Internal")
            and not re.match(r"Version .* Page \d+ of \d+", ln)
        ]
        # PDF text breaks lines mid-sentence: glue wrapped lines back into paragraphs,
        # but keep section headings such as "4. Probation" on their own line.
        paras, current = [], ""
        for ln in lines:
            if re.match(r"^\d+\. [A-Z][\w ,&-]{2,60}$", ln):      # a heading
                paras += [current, ln] if current else [ln]
                current = ""
            elif current and not current.endswith((".", ":", "!", "?")):
                current += " " + ln                                 # wrapped line
            else:
                if current:
                    paras.append(current)
                current = ln
        if current:
            paras.append(current)
        text = "\n\n".join(paras)
        records.append({
            "text": text.strip(),
            "metadata": {"source": path.name, "page": page_no, "office": "all"},
        })
    return records


def load_markdown(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    text = text.replace("**", "")          # bold markers carry no meaning for search
    return [{"text": text, "metadata": {"source": path.name, "office": office_from_name(path)}}]


def load_html(path: Path) -> list[dict]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for junk in soup.select("nav, footer, script, style, .cookie-banner"):
        junk.decompose()                   # delete menus, footers, scripts, banners
    main = soup.find("main") or soup.body
    parts = []
    for el in main.find_all(["h1", "h2", "h3", "p", "li"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if el.name in ("h1", "h2", "h3"):
            parts.append(f"\n{'#' * int(el.name[1])} {txt}")   # keep headings, markdown-style
        else:
            parts.append(txt)
    return [{"text": "\n".join(parts).strip(),
             "metadata": {"source": path.name, "office": office_from_name(path)}}]


def load_csv(path: Path) -> list[dict]:
    """Each FAQ row is already a perfect small chunk: keep one record per row."""
    records = []
    with path.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            records.append({
                "text": f"Q: {row['question']}\nA: {row['answer']}",
                "metadata": {"source": path.name, "row": i, "office": row.get("office", "all"),
                             "is_faq": True},
            })
    return records


LOADERS = {".pdf": load_pdf, ".md": load_markdown, ".html": load_html, ".csv": load_csv}


def load_all(data_dir: Path) -> list[dict]:
    records = []
    for path in sorted(data_dir.iterdir()):
        loader = LOADERS.get(path.suffix.lower())
        if loader:
            records.extend(loader(path))
    return records
