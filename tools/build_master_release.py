import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DELIVERABLES = ROOT / "deliverables"
DELIVERABLES.mkdir(parents=True, exist_ok=True)

out_zip = DELIVERABLES / "RAIR_Master_Research_Release.zip"

print(f"[RELEASE] Building Master Research Archive: {out_zip}")

files_to_pack = [
    # Technical Report & Documentation
    ("docs/PROJECT_MASTER_DOCUMENTATION.md", "docs/PROJECT_MASTER_DOCUMENTATION.md"),
    ("docs/RAIR_TECHNICAL_REPORT.md", "docs/RAIR_TECHNICAL_REPORT.md"),
    ("docs/RAIR_TEST.md", "docs/RAIR_TEST.md"),
    ("docs/RAIR_SCALE.md", "docs/RAIR_SCALE.md"),
    ("docs/RAIR_V3.md", "docs/RAIR_V3.md"),
    ("docs/RAIR_V2.md", "docs/RAIR_V2.md"),
    ("docs/RESEARCH_DASHBOARD.md", "docs/RESEARCH_DASHBOARD.md"),

    # Test Cohort Deliverables
    ("deliverables/rair_test/START_HERE.md", "rair_test/START_HERE.md"),
    ("deliverables/rair_test/RAIR_Test_Outcome_Census.csv", "rair_test/RAIR_Test_Outcome_Census.csv"),
    ("deliverables/rair_test/RAIR_Test_Findings.md", "rair_test/RAIR_Test_Findings.md"),
    ("deliverables/rair_test/RAIR_Test_Failure_Review.md", "rair_test/RAIR_Test_Failure_Review.md"),
    ("deliverables/rair_test/RAIR_Test_Presentation.md", "rair_test/RAIR_Test_Presentation.md"),

    # Scale Cohort Deliverables
    ("deliverables/rair_scale/START_HERE.md", "rair_scale/START_HERE.md"),
    ("deliverables/rair_scale/RAIR_Scale_Outcome_Census.csv", "rair_scale/RAIR_Scale_Outcome_Census.csv"),
    ("deliverables/rair_scale/RAIR_Scale_Findings.md", "rair_scale/RAIR_Scale_Findings.md"),
    ("deliverables/rair_scale/RAIR_Scale_Failure_Review.md", "rair_scale/RAIR_Scale_Failure_Review.md"),
    ("deliverables/rair_scale/RAIR_Scale_Presentation.md", "rair_scale/RAIR_Scale_Presentation.md"),

    # Configs & Summaries
    ("config/rair_test_manifest.json", "config/rair_test_manifest.json"),
    ("config/rair_test_settings.json", "config/rair_test_settings.json"),
    ("results/rair_test/rair_test_benchmark.summary.json", "results/rair_test/rair_test_benchmark.summary.json"),
    ("results/rair_scale/rair_scale_benchmark.summary.json", "results/rair_scale/rair_scale_benchmark.summary.json"),
]

with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for src_rel, arc_rel in files_to_pack:
        src_path = ROOT / src_rel
        if src_path.exists():
            z.write(src_path, arcname=arc_rel)
            print(f"  + Added: {arc_rel} ({src_path.stat().st_size / 1024:.1f} KB)")
        else:
            print(f"  ! Warning: {src_rel} not found")

print(f"\n[SUCCESS] Master Research Release Archive created: {out_zip}")
print(f"Total size: {out_zip.stat().st_size / 1024:.1f} KB")

