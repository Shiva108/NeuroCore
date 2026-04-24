import pytest

from neurocore.retrieval.rankers import SentenceTransformersRanker


def test_sentence_transformers_ranker_requires_optional_dependency():
    with pytest.raises(RuntimeError, match="sentence-transformers"):
        SentenceTransformersRanker("sentence-transformers/all-MiniLM-L6-v2")
