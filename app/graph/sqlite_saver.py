"""
Custom SqliteSaver — persistent conversation checkpointing using SQLite.
Implements the same interface as MemorySaver without external dependencies.
Workaround for langgraph-checkpoint-sqlite version conflict with langgraph 0.2.45.
"""

import base64
import sqlite3
import threading
from typing import Iterator, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class SqliteSaver(BaseCheckpointSaver):

    def __init__(self, db_path: str = "data/checkpoints.db"):
        super().__init__(serde=JsonPlusSerializer())
        self.db_path = db_path
        self._lock = threading.Lock()
        self._setup()

    def _setup(self):
        import os
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint BLOB NOT NULL,
                    metadata_type TEXT,
                    metadata BLOB NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    type TEXT,
                    value BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
            """)
            conn.commit()

    def _encode(self, data) -> str:
        """Encode data to base64 string for safe SQLite storage."""
        if isinstance(data, bytes):
            return base64.b64encode(data).decode("ascii")
        return base64.b64encode(data.encode("utf-8")).decode("ascii")

    def _decode(self, data) -> bytes:
        """Decode base64 string back to bytes for deserialization."""
        if isinstance(data, bytes):
            return base64.b64decode(data)
        return base64.b64decode(data.encode("ascii"))

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")

        with sqlite3.connect(self.db_path) as conn:
            if checkpoint_id:
                row = conn.execute(
                    "SELECT type, checkpoint, metadata_type, metadata, parent_checkpoint_id "
                    "FROM checkpoints WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?",
                    (thread_id, checkpoint_ns, checkpoint_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT type, checkpoint, metadata_type, metadata, parent_checkpoint_id, checkpoint_id "
                    "FROM checkpoints WHERE thread_id=? AND checkpoint_ns=? "
                    "ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id, checkpoint_ns)
                ).fetchone()

        if not row:
            return None

        if checkpoint_id:
            type_, checkpoint_data, metadata_type, metadata_data, parent_id = row
        else:
            type_, checkpoint_data, metadata_type, metadata_data, parent_id, checkpoint_id = row

        checkpoint = self.serde.loads_typed((
            type_ or "msgpack",
            self._decode(checkpoint_data)
        ))
        metadata = self.serde.loads_typed((
            metadata_type or "msgpack",
            self._decode(metadata_data)
        ))

        config_out = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }
        parent_config = (
            {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_id,
                }
            }
            if parent_id else None
        )

        return CheckpointTuple(
            config=config_out,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
        )

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        if not config:
            return

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT checkpoint_id, type, checkpoint, metadata_type, metadata, parent_checkpoint_id "
                "FROM checkpoints WHERE thread_id=? AND checkpoint_ns=? "
                "ORDER BY checkpoint_id DESC",
                (thread_id, checkpoint_ns)
            ).fetchall()

        for checkpoint_id, type_, checkpoint_data, metadata_type, metadata_data, parent_id in rows:
            checkpoint = self.serde.loads_typed((
                type_ or "msgpack",
                self._decode(checkpoint_data)
            ))
            metadata = self.serde.loads_typed((
                metadata_type or "msgpack",
                self._decode(metadata_data)
            ))
            config_out = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }
            parent_config = (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_id,
                    }
                }
                if parent_id else None
            )
            yield CheckpointTuple(
                config=config_out,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
            )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[dict] = None,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        checkpoint_type, checkpoint_data = self.serde.dumps_typed(checkpoint)
        metadata_type, metadata_data = self.serde.dumps_typed(metadata)

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO checkpoints "
                    "(thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, "
                    "type, checkpoint, metadata_type, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        parent_checkpoint_id,
                        checkpoint_type,
                        self._encode(checkpoint_data),
                        metadata_type,
                        self._encode(metadata_data),
                    )
                )
                conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list,
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id", "")

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                for idx, write in enumerate(writes):
                    channel, value = write[0], write[1]
                    type_str, value_bytes = self.serde.dumps_typed(value)
                    conn.execute(
                        "INSERT OR REPLACE INTO checkpoint_writes "
                        "(thread_id, checkpoint_ns, checkpoint_id, task_id, "
                        "idx, channel, type, value) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            task_id,
                            idx,
                            channel,
                            type_str,
                            self._encode(value_bytes),
                        )
                    )
                conn.commit()