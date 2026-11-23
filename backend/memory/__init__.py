"""SQLite persistence for conversations and LangGraph state.

The LangGraph checkpointer owns ``checkpoints.sqlite``. This package owns
``app.sqlite``, which stores conversation metadata such as titles and
timestamps. Keeping the two separate means app data is independent of the
checkpointer's internal schema.
"""

from backend.memory.db import ensure_data_dir, init_app_db, open_app_db

__all__ = ["ensure_data_dir", "init_app_db", "open_app_db"]
