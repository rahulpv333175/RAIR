"""Run the local competitive KAIR baseline with the shared diagnostic writer."""

from src.experiments.run_rair import main as run_diagnostic
from src.kair.controller import KAIRController


def main(argv: list[str] | None = None) -> int:
    return run_diagnostic(argv, controller_type=KAIRController, system="KAIR")


if __name__ == "__main__":
    raise SystemExit(main())
