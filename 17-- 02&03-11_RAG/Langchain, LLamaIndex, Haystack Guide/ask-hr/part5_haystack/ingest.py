"""Haystack indexing pipeline: route -> convert -> clean -> split -> tag -> embed -> write.
Run:  python -m part5_haystack.ingest
"""
from pathlib import Path

from haystack import Document, Pipeline, component
from haystack.components.converters import (CSVToDocument, HTMLToDocument, PyPDFToDocument,
                                            TextFileToDocument)
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentCleaner, RecursiveDocumentSplitter
from haystack.components.routers import FileTypeRouter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.embedders.sentence_transformers import (
    SentenceTransformersDocumentEmbedder)

import config
from part2_by_hand.loaders import office_from_name
from part5_haystack.store import get_document_store


@component
class AddSourceAndOffice:
    """Custom component: give every Document a short `source` and an `office`."""

    @component.output_types(documents=list[Document])
    def run(self, documents: list[Document]):
        for doc in documents:
            path = Path(doc.meta.get("file_path", "unknown"))
            doc.meta["source"] = path.name
            doc.meta.setdefault("office", office_from_name(path))
        return {"documents": documents}


def build_indexing_pipeline(document_store) -> Pipeline:
    p = Pipeline()
    p.add_component("router", FileTypeRouter(
        mime_types=["application/pdf", "text/markdown", "text/html", "text/csv"],
        additional_mimetypes={"text/markdown": ".md"},
    ))
    p.add_component("pdf", PyPDFToDocument())
    p.add_component("md", TextFileToDocument())
    p.add_component("html", HTMLToDocument())             # strips menus/footers itself
    p.add_component("csv", CSVToDocument(conversion_mode="row"))   # one Document per row
    p.add_component("prose", DocumentJoiner())            # pdf + md + html -> one list
    p.add_component("cleaner", DocumentCleaner(
        remove_regex=r"Nimbus Corp Employee Handbook - Internal|Version 2026\.1 - Confidential - Page \d+ of \d+",
        remove_empty_lines=False, remove_extra_whitespaces=False,   # keep paragraph breaks
    ))
    p.add_component("splitter", RecursiveDocumentSplitter(
        split_length=config.CHUNK_SIZE, split_overlap=config.CHUNK_OVERLAP, split_unit="char",
        separators=["\n\n", "sentence", "\n", " "],
    ))
    p.add_component("all", DocumentJoiner())              # chunks + FAQ rows
    p.add_component("tagger", AddSourceAndOffice())
    p.add_component("embedder", SentenceTransformersDocumentEmbedder(
        model=config.EMBED_MODEL, normalize_embeddings=True,
        meta_fields_to_embed=["question"],                # FAQ: embed question + answer
    ))
    p.add_component("writer", DocumentWriter(document_store, policy=DuplicatePolicy.OVERWRITE))

    p.connect("router.application/pdf", "pdf.sources")
    p.connect("router.text/markdown", "md.sources")
    p.connect("router.text/html", "html.sources")
    p.connect("router.text/csv", "csv.sources")
    p.connect("pdf", "prose")
    p.connect("md", "prose")
    p.connect("html", "prose")
    p.connect("prose", "cleaner")
    p.connect("cleaner", "splitter")
    p.connect("splitter", "all")
    p.connect("csv", "all")                               # FAQ rows skip the splitter
    p.connect("all", "tagger")
    p.connect("tagger", "embedder")
    p.connect("embedder", "writer")
    return p


def main():
    store = get_document_store()
    store.delete_all_documents()                          # rebuild from scratch
    pipeline = build_indexing_pipeline(store)
    files = sorted(str(p) for p in config.DATA_DIR.iterdir())
    result = pipeline.run({"router": {"sources": files},
                           "csv": {"content_column": "answer"}})
    print(f"Wrote {result['writer']['documents_written']} chunks; store has {store.count_documents()}")


if __name__ == "__main__":
    main()
