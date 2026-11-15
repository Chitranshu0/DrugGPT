"""DrugGPT maintenance CLI.

Index, check, and test commands. The FastAPI backend and Streamlit frontend
have their own entrypoints: ``python main.py`` and ``python app.py``.

Run with ``python -m src.cli`` or the ``druggpt`` console script::

    python -m src.cli index       # rebuild the Chroma index from data/raw
    python -m src.cli check       # print resolved config + API health
    python -m src.cli test        # run the pytest suite
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _run(args: list[str], env: dict[str, str] | None = None) -> int:
    return subprocess.run(args, env=env or _env()).returncode


def cmd_index(args: argparse.Namespace) -> int:
    from src.core.config import Settings
    from src.rag.indexing import rebuild_index

    if args.data_dir:
        os.environ["DRUGGPT_DATA_DIR"] = args.data_dir
    settings = Settings.from_env()
    settings.ensure_directories()
    settings.validate()
    result = rebuild_index(settings)
    print(result)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    import urllib.request

    from src.core.config import PROJECT_ROOT, Settings

    if args.data_dir:
        os.environ["DRUGGPT_DATA_DIR"] = args.data_dir
    settings = Settings.from_env()
    settings.ensure_directories()
    settings.validate()

    print("== DrugGPT configuration ==")
    print(f"  project_root : {PROJECT_ROOT}")
    print(f"  data_dir     : {settings.data_dir}")
    print(f"  groq_api_key : {'set' if settings.groq_api_key else 'NOT SET'}")
    print(f"  groq_model   : {settings.groq_model}")
    print(f"  threshold    : {settings.relevance_threshold}")
    print(f"  retrieval_k  : {settings.retrieval_k}")
    print(f"  api_host     : {settings.api_host}")
    print(f"  api_port     : {settings.api_port}")
    print(f"  ui_port      : {settings.ui_port}")

    base_url = f"http://{settings.api_host}:{settings.api_port}"
    try:
        with urllib.request.urlopen(base_url + "/health", timeout=3) as response:
            print(f"  api_health   : {response.read().decode().strip()}")
    except Exception as exc:  # noqa: BLE001 - surface connection problems clearly
        print(f"  api_health   : unreachable ({exc})")

    return 0


def cmd_test(args: argparse.Namespace) -> int:
    return _run([sys.executable, "-m", "pytest"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="druggpt", description="DrugGPT maintenance CLI")
    sub = parser.add_subparsers(dest="command")

    p_index = sub.add_parser("index", help="rebuild the Chroma index from data/raw")
    p_index.add_argument("--data-dir", default=None)
    p_index.set_defaults(func=cmd_index)

    p_check = sub.add_parser("check", help="print resolved config and API health")
    p_check.add_argument("--data-dir", default=None)
    p_check.set_defaults(func=cmd_check)

    p_test = sub.add_parser("test", help="run the test suite")
    p_test.set_defaults(func=cmd_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
