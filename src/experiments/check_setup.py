"""Phase 1 smoke test. No network requests or LLM inference."""

import importlib
import platform
import sys

from src.settings import PROJECT_ROOT, load_settings


PACKAGES = (
    "src",
    "src.llm",
    "src.retrieval",
    "src.datasets",
    "src.evaluation",
    "src.rair",
    "src.kair",
    "src.experiments",
)


def main() -> int:
    try:
        if sys.version_info < (3, 11):
            raise ValueError("Use Python 3.11 or newer for this project.")

        settings = load_settings()

        for name in PACKAGES:
            marker = PROJECT_ROOT.joinpath(*name.split("."), "__init__.py")
            if not marker.is_file():
                raise FileNotFoundError(f"Missing package marker: {marker}")
            importlib.import_module(name)

        folders = ["config", "docs", "tests", *settings["paths"].values()]
        for folder in folders:
            path = PROJECT_ROOT / folder
            if not path.is_dir():
                raise FileNotFoundError(f"Missing folder: {path}")

        if settings["retrieval"].get("web_enabled") is not False:
            raise ValueError("Keep retrieval.web_enabled set to false.")
        if settings["llm"].get("max_concurrent_requests") != 1:
            raise ValueError("Use one concurrent LLM request for initial setup.")
        if settings["kair"].get("num_agents") != 2:
            raise ValueError("The initial KAIR baseline should have two agents.")

        print(f"[OK] Python {platform.python_version()}")
        print(f"[OK] Package imports: {len(PACKAGES)}")
        print("[OK] Project folders exist")
        print("[OK] config/settings.yaml loaded")
        print(f"[INFO] Configured model: {settings['llm']['model']}")
        print(f"[INFO] Configured context: {settings['llm']['num_ctx']}")
        print(f"[INFO] KAIR agents: {settings['kair']['num_agents']}")
        print("[INFO] Ollama, GPU, and dataset have NOT been tested")
        print("PHASE 1 PASSED")
        return 0

    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())