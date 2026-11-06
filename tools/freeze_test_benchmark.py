import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluation.paired import fingerprint

test_dir = ROOT / "results" / "rair_test"
test_dir.mkdir(parents=True, exist_ok=True)

manifest_path = ROOT / "config" / "rair_test_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest_hash = fingerprint(manifest)

freeze_data = {
    "title": "RAIR Extended Held-Out Test Benchmark (200 Runs)",
    "date": "4 November 2026",
    "cohort_size": 50,
    "runs": 200,
    "seeds": [42, 43],
    "manifest_sha256": manifest_hash,
    "exclusions_count": len(manifest["settings"]["evaluation"]["exclude_question_ids"]),
    "budget": {"max_retrieval_calls": 4, "max_llm_calls": 18},
    "corpus": "per_question local BM25 top-3 pools",
    "model": "qwen3.5:4b via Ollama 0.40.13",
    "hardware": "NVIDIA GeForce RTX 4060 Laptop GPU",
}

freeze_path = test_dir / "rair_test_freeze.json"
with open(freeze_path, "w", encoding="utf-8") as f:
    json.dump(freeze_data, f, indent=2, ensure_ascii=False)
print(f"Created freeze metadata: {freeze_path}")

snapshot_zip = test_dir / "rair_test_source_snapshot.zip"
with zipfile.ZipFile(snapshot_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for py_file in (ROOT / "src").rglob("*.py"):
        z.write(py_file, arcname=str(py_file.relative_to(ROOT)))
    z.write(manifest_path, arcname="config/rair_test_manifest.json")
    z.write(ROOT / "config" / "rair_test_settings.json", arcname="config/rair_test_settings.json")
print(f"Created code snapshot zip: {snapshot_zip} ({snapshot_zip.stat().st_size / 1024:.1f} KB)")

