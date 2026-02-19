"""
Mock AI Overview (AIO) client.

In production this would call the real Google Search API / Serp API.
For the MVP it returns deterministic mock data per query so the entire
pipeline can be validated without external credentials.
"""
import hashlib

# A small corpus of mock AIO responses keyed by a hash of the query text.
# Any query NOT in this corpus returns None (simulates "aio_not_found").
_MOCK_CORPUS: dict[str, str] = {
    # keyword: "python fastapi tutorial"
    "python fastapi": (
        "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ "
        "based on standard Python type hints. It is one of the fastest Python frameworks available, "
        "rivalling NodeJS and Go. Key features include automatic OpenAPI documentation generation, "
        "native async support via ASGI, and data validation powered by Pydantic. "
        "FastAPI encourages dependency injection and supports OAuth2 and JWT out of the box."
    ),
    # keyword: "gap analysis seo"
    "gap analysis": (
        "A content gap analysis identifies topics and keywords that competitors rank for but your "
        "website does not. The process involves auditing existing content, analysing competitor pages, "
        "mapping customer journey stages, and prioritising new content opportunities. "
        "Tools commonly used include Ahrefs, SEMrush, and Screaming Frog. "
        "Effective gap analyses improve organic visibility, user engagement, and conversion rates."
    ),
    # keyword: "machine learning basics"
    "machine learning": (
        "Machine learning is a branch of artificial intelligence where algorithms learn patterns "
        "from data without being explicitly programmed. Core categories include supervised learning, "
        "unsupervised learning, and reinforcement learning. Popular algorithms are linear regression, "
        "decision trees, random forests, support vector machines, and neural networks. "
        "Python libraries such as scikit-learn, TensorFlow, and PyTorch are widely used."
    ),
}


async def fetch_aio(query: str) -> str | None:
    """
    Return a mock AI Overview text for *query*, or None when not found.

    Matching is done on any substring from the corpus appearing in the
    lower-cased query, making it flexible for varied inputs.
    """
    q_lower = query.lower()
    for keyword, text in _MOCK_CORPUS.items():
        if keyword in q_lower:
            return text
    return None
