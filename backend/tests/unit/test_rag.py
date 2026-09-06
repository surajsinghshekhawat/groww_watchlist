"""RAG retrieval unit tests (no network required for docs path)."""

from app.explanation.rag import retrieve_documents


def test_retrieve_hdfc_filing_doc() -> None:
    chunks = retrieve_documents("HDFCBANK board capital allocation filing", top_k=3)
    assert chunks
    joined = " ".join(c.text for c in chunks).upper()
    assert "HDFC" in joined or "BOARD" in joined
