"""Локальний векторний індекс над нотатками vault (ПР7).

Індекс похідний: джерелом істини лишаються .md-файли vault. Він зберігається в каталозі
(за замовчуванням `.index/`, додано в .gitignore) і перебудовується автоматично, якщо вміст vault змінився.

Бекенди ембедингів:
  lsa  – TF-IDF по символьних n-грамах + SVD (scikit-learn); працює без мережі й завантажень.
  st   – sentence-transformers (якщо встановлено); семантичні ембединги.
  auto – st, якщо доступний, інакше lsa (змінна VETCARE_EMBEDDINGS).
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

SKIP_DIRS = {"Templates", "scripts", ".git"}
_FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
DEFAULT_ST_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class Chunk:
    title: str
    path: str
    text: str


def chunk_note(title: str, path: str, text: str) -> list[Chunk]:
    """Розбиває нотатку на фрагменти за заголовками другого рівня; кожен фрагмент починається з назви."""
    body = _FRONT.sub("", text).strip()
    parts = re.split(r"\n(?=## )", body)
    chunks = []
    for part in parts:
        content = re.sub(r"^# .*\n?", "", part.strip()).strip()
        if content:
            chunks.append(Chunk(title, path, f"{title}. {content}"))
    return chunks or [Chunk(title, path, title)]


def collect_chunks(vault_root: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for p in sorted(vault_root.rglob("*.md")):
        rel = p.relative_to(vault_root)
        if set(rel.parts) & SKIP_DIRS or p.name == "README.md":
            continue
        chunks.extend(chunk_note(p.stem, str(rel), p.read_text(encoding="utf-8")))
    return chunks


def fingerprint(chunks: list[Chunk], backend: str) -> str:
    h = hashlib.sha256(backend.encode())
    for c in chunks:
        h.update(c.path.encode())
        h.update(c.text.encode())
    return h.hexdigest()


class LsaEmbedder:
    name = "lsa"

    def __init__(self, dims: int = 100):
        self.dims = dims
        self.vectorizer = None
        self.svd = None

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, lowercase=True)
        tfidf = self.vectorizer.fit_transform(texts)
        k = max(2, min(self.dims, tfidf.shape[0] - 1, tfidf.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=42)
        return _normalize(self.svd.fit_transform(tfidf))

    def transform(self, texts: list[str]) -> np.ndarray:
        return _normalize(self.svd.transform(self.vectorizer.transform(texts)))


class SentenceTransformerEmbedder:
    """Семантичні ембединги (потребує пакета sentence-transformers і завантаження моделі)."""

    name = "st"

    def __init__(self, model: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model or os.environ.get("VETCARE_EMBED_MODEL", DEFAULT_ST_MODEL))

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    def transform(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


def make_embedder(kind: str | None = None):
    kind = (kind or os.environ.get("VETCARE_EMBEDDINGS", "auto")).lower()
    if kind in ("st", "auto"):
        try:
            return SentenceTransformerEmbedder()
        except Exception:  # пакет не встановлено або модель недоступна
            if kind == "st":
                raise
    return LsaEmbedder()


class VectorIndex:
    def __init__(self, chunks: list[Chunk], matrix: np.ndarray, embedder, fp: str):
        self.chunks, self.matrix, self.embedder, self.fp = chunks, matrix, embedder, fp

    @property
    def backend(self) -> str:
        return self.embedder.name

    @classmethod
    def build(cls, vault_root: Path, embedder=None) -> VectorIndex:
        embedder = embedder or make_embedder()
        chunks = collect_chunks(vault_root)
        matrix = embedder.fit_transform([c.text for c in chunks])
        return cls(chunks, matrix, embedder, fingerprint(chunks, embedder.name))

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump((self.chunks, self.matrix, self.embedder, self.fp), index_dir / "index.joblib")

    @classmethod
    def load_or_build(cls, vault_root: Path, index_dir: Path, kind: str | None = None) -> VectorIndex:
        """Завантажує збережений індекс, якщо vault не змінився, інакше перебудовує його."""
        embedder_kind = (kind or os.environ.get("VETCARE_EMBEDDINGS", "auto")).lower()
        chunks = collect_chunks(vault_root)
        file = index_dir / "index.joblib"
        if file.exists():
            try:
                saved_chunks, matrix, embedder, fp = joblib.load(file)
                wanted = {"lsa": "lsa", "st": "st"}.get(embedder_kind)
                if fp == fingerprint(chunks, embedder.name) and (wanted is None or wanted == embedder.name):
                    return cls(saved_chunks, matrix, embedder, fp)
            except Exception:  # пошкоджений або несумісний індекс перебудовуємо
                pass
        idx = cls.build(vault_root, make_embedder(embedder_kind))
        idx.save(index_dir)
        return idx

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Повертає до `limit` нотаток за найкращим фрагментом (косинусна близькість)."""
        q = self.embedder.transform([query])[0]
        scores = self.matrix @ q
        best: dict[str, tuple[float, int]] = {}
        for i, s in enumerate(scores):
            t = self.chunks[i].title
            if t not in best or s > best[t][0]:
                best[t] = (float(s), i)
        ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:limit]
        return [
            {"title": t, "path": self.chunks[i].path, "snippet": self.chunks[i].text[:120].replace("\n", " "),
             "score": round(s, 4)}
            for t, (s, i) in ranked
        ]
