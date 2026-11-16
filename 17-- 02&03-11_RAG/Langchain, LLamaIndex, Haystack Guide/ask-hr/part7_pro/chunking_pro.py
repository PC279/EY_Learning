"""Structure-aware chunking with contextual headers (7.2a).
Every chunk starts with a line saying which document and section it comes from."""
import re

from part2_by_hand.chunking import chunk_text

HEADING = re.compile(r"^(#{1,3} .+|\d+\. [A-Z][\w ,&-]{2,60})$")   # '## 2. Carry...' or '4. Probation'


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return (heading, body) pairs. Text before the first heading gets heading ''."""
    sections, heading, body = [], "", []
    for line in text.splitlines():
        if HEADING.match(line.strip()):
            if "\n".join(body).strip():
                sections.append((heading, "\n".join(body).strip()))
            heading, body = line.strip().lstrip("# ").strip(), []
        else:
            body.append(line)
    if "\n".join(body).strip():
        sections.append((heading, "\n".join(body).strip()))
    return sections


def chunk_with_headers(record: dict, size: int, overlap: int) -> list[dict]:
    meta = record["metadata"]
    if meta.get("is_faq"):
        return [{"text": record["text"], "metadata": dict(meta, chunk=0, section="FAQ")}]

    text = record["text"]
    h1 = re.search(r"^# (.+)$", text, re.M)               # a Markdown/HTML title, if any
    title = h1.group(1).strip() if h1 else meta["source"].rsplit(".", 1)[0].replace("_", " ").title()
    sections = split_sections(text)
    office = {"india": "India (Bengaluru)", "germany": "Germany (Berlin)"}.get(meta["office"], "all offices")
    out = []
    for heading, body in sections:
        heading = "" if heading == title else heading         # the title is not a section
        header = f"[{title} | {heading or 'Introduction'} | applies to: {office}]"
        for piece in chunk_text(body, size - len(header) - 1, overlap):
            out.append({
                "text": f"{header}\n{piece}",
                "metadata": dict(meta, chunk=len(out), section=heading or "Introduction"),
            })
    return out


def chunk_records_pro(records: list[dict], size: int, overlap: int) -> list[dict]:
    return [c for rec in records for c in chunk_with_headers(rec, size, overlap)]
