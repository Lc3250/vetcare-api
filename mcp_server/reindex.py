"""Примусова переіндексація vault: python -m mcp_server.reindex"""
import os
from pathlib import Path

from mcp_server.vector_index import VectorIndex, make_embedder

if __name__ == "__main__":
    vault = Path(os.environ["VETCARE_VAULT_PATH"])
    index_dir = Path(os.environ.get("VETCARE_INDEX_DIR", Path(__file__).resolve().parent.parent / ".index"))
    idx = VectorIndex.build(vault, make_embedder())
    idx.save(index_dir)
    print(f"Індекс побудовано: {len(idx.chunks)} фрагментів, бекенд {idx.backend}, каталог {index_dir}")
