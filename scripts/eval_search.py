"""Порівняльне тестування search_notes: точний збіг підрядка до і після підключення векторного індексу.

Режими:
  exact-питання  – збіг підрядка за повним текстом питання (поведінка search_notes до ПР7)
  exact-ключове  – збіг підрядка за одним ключовим словом із eval/questions.json (агент сам добирає слово)
  vector         – семантичний пошук за повним текстом питання (search_notes після ПР7)
Метрики: hit@1, hit@3 (чи є очікувана нотатка серед перших k), MRR (за першою очікуваною нотаткою в топ-5).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcp_server.vault_store import VaultStore  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def rank(hits, expected):
    for i, h in enumerate(hits, 1):
        if h["title"] in expected:
            return i
    return None


def main():
    vault = os.environ["VETCARE_VAULT_PATH"]
    questions = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
    commit = subprocess.run(["git", "-C", vault, "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        exact = VaultStore(vault, push=False, search_mode="exact")
        vector = VaultStore(vault, push=False, search_mode="vector", index_dir=tmp)
        backend = None
        rows = []
        for q in questions:
            row = {"id": q["id"], "level": q["level"], "question": q["question"], "expected": q["expected"]}
            runs = {
                "exact-питання": exact.search_notes(q["question"], 5),
                "exact-ключове": exact.search_notes(q["keyword"], 5),
                "vector": vector.search_notes(q["question"], 5),
            }
            for mode, hits in runs.items():
                row[mode] = {"rank": rank(hits, q["expected"]), "top3": [h["title"] for h in hits[:3]]}
            rows.append(row)
        from mcp_server.vector_index import VectorIndex
        backend = VectorIndex.load_or_build(Path(vault), Path(tmp)).backend
    summary = {}
    for mode in ("exact-питання", "exact-ключове", "vector"):
        ranks = [r[mode]["rank"] for r in rows]
        summary[mode] = {
            "hit@1": sum(1 for x in ranks if x == 1),
            "hit@3": sum(1 for x in ranks if x is not None and x <= 3),
            "mrr": round(sum(1 / x for x in ranks if x) / len(ranks), 3),
        }
    out = {"vault_commit": commit, "backend": backend, "questions": len(rows), "summary": summary, "rows": rows}
    (ROOT / "eval" / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"vault {commit}, бекенд {backend}")
    for mode, s in summary.items():
        print(f"{mode:15} hit@1={s['hit@1']}/10 hit@3={s['hit@3']}/10 MRR={s['mrr']}")
    for r in rows:
        print(r["id"], {m: r[m]["rank"] for m in summary})


if __name__ == "__main__":
    main()
