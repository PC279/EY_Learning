"""LangChain indexing pipeline: loaders -> splitter -> embeddings -> Chroma.
Run:  python -m part3_langchain.ingest
"""
from pathlib import Path

from langchain_community.document_loaders import CSVLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from part2_by_hand.loaders import load_html, office_from_name   # our own cleaner, reused
from part3_langchain.store import get_vectorstore


def load_documents(data_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(data_dir.iterdir()):
        if path.suffix == ".pdf":
            pages = PyPDFLoader(str(path)).load()          # one Document per page
            for d in pages:                                # drop the repeating header/footer
                d.page_content = "\n".join(
                    ln for ln in d.page_content.splitlines()
                    if not ln.startswith(("Nimbus Corp Employee Handbook - Internal", "Version 2026"))
                )
            docs += pages
        elif path.suffix == ".md":
            docs += TextLoader(str(path), encoding="utf-8").load()
        elif path.suffix == ".csv":
            docs += CSVLoader(str(path), encoding="utf-8",
                              content_columns=["question", "answer"],
                              metadata_columns=["office"]).load()   # one Document per row
        elif path.suffix == ".html":
            # Generic HTML loaders keep menus and footers; our cleaner from Part 2 doesn't.
            docs += [Document(page_content=r["text"], metadata=r["metadata"])
                     for r in load_html(path)]

    for d in docs:                                         # normalise metadata
        src = Path(d.metadata["source"])
        d.metadata["source"] = src.name                    # loaders store the full path
        d.metadata.setdefault("office", office_from_name(src))
        if "page" in d.metadata:
            d.metadata["page"] += 1                        # PyPDFLoader counts pages from 0
    return docs


def main():
    docs = load_documents(config.DATA_DIR)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],         # same idea as our chunk_text
        add_start_index=True,                              # records where each chunk began
    )
    faq = [d for d in docs if d.metadata["source"].endswith(".csv")]
    rest = [d for d in docs if not d.metadata["source"].endswith(".csv")]
    chunks = faq + splitter.split_documents(rest)          # FAQ rows are already small

    ids = [f"{c.metadata['source']}::{c.metadata.get('page', c.metadata.get('row', 0))}"
           f"::{c.metadata.get('start_index', 0)}" for c in chunks]

    vectorstore = get_vectorstore()
    vectorstore.reset_collection()                         # simplest way to avoid stale chunks
    vectorstore.add_documents(chunks, ids=ids)
    print(f"{len(docs)} documents -> {len(chunks)} chunks stored")


if __name__ == "__main__":
    main()
