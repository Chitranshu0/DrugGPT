"""Environment shims applied *before* heavy ML imports.

Import :func:`configure_runtime` first in the backend entrypoint (the uvicorn
target) so that TensorFlow is never pulled in through
``transformers``/``datasets``. TensorFlow is unused and adds startup time plus
oneDNN/tf_keras warnings on the PyTorch embedding path.
"""

from __future__ import annotations

import os
import warnings

_TF_SHIMS = {
    "USE_TF": "0",
    "TRANSFORMERS_NO_TF": "1",
    "TF_CPP_MIN_LOG_LEVEL": "3",
}

_CONFIGURED = False


def configure_runtime() -> None:
    """Set no-TensorFlow defaults and silence the Python-EOL dependency notice.

    Safe to call repeatedly. ``setdefault`` means an explicit operator override
    in ``.env`` or the shell always wins.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    for key, value in _TF_SHIMS.items():
        os.environ.setdefault(key, value)
    warnings.filterwarnings(
        "ignore",
        message=r"You are using a Python version .*Google will stop supporting",
        category=FutureWarning,
    )
    _CONFIGURED = True
