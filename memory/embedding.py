"""Local embedding via BAAI/bge-small-zh-v1.5 (~90MB, CPU-friendly, Chinese-optimized)."""
import pickle
import numpy as np
from pathlib import Path

_model = None
EMBED_DIM = 512


def _load():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("[embedding] loading BAAI/bge-small-zh-v1.5 ...")
        _model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        print("[embedding] model ready")
    return _model


def encode(text: str) -> np.ndarray:
    m = _load()
    vec = m.encode(text, normalize_embeddings=True)
    return vec.astype(np.float32)


def encode_batch(texts: list[str]) -> list[np.ndarray]:
    m = _load()
    vecs = m.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [v.astype(np.float32) for v in vecs]


def to_blob(vec: np.ndarray) -> bytes:
    return pickle.dumps(vec)


def from_blob(blob: bytes) -> np.ndarray:
    return pickle.loads(blob)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # already normalized
