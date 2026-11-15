"""DrugGPT Streamlit frontend entrypoint.

Run:
    python app.py                         # start the Streamlit frontend (:8501)
    python app.py --api-url http://localhost:8000
    python app.py --port 8502
    streamlit run src/ui/app.py           # alternative
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

from src.core.config import settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(prog="app", description="DrugGPT Streamlit frontend")
    parser.add_argument(
        "--api-url",
        default=None,
        help="Backend API URL (default: http://{api_host}:{api_port} from .env)",
    )
    parser.add_argument("--port", type=int, default=settings.ui_port, help="Streamlit server port")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    if args.api_url:
        env["DRUGGPT_API_URL"] = args.api_url
    else:
        env.setdefault(
            "DRUGGPT_API_URL",
            f"http://{settings.api_host}:{settings.api_port}",
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(REPO_ROOT / "src" / "ui" / "app.py"),
            "--server.port",
            str(args.port),
        ],
        env=env,
    )


if __name__ == "__main__":
    main()
