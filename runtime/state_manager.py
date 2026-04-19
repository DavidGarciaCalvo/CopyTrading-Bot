import json
import os
from datetime import datetime, UTC


class RuntimeStateManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.runtime_dir = os.path.join(base_dir, "runtime")
        self.state_file = os.path.join(self.runtime_dir, "runtime_state.json")
        self._ensure_runtime_dir()

    def _ensure_runtime_dir(self):
        os.makedirs(self.runtime_dir, exist_ok=True)

    def _utc_now(self):
        return datetime.now(UTC).isoformat()

    def _read_state(self):
        if not os.path.exists(self.state_file):
            return {}

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def initialize(self, balance_actual=0.0, open_positions=0):
        now = self._utc_now()
        state = {
            "running": True,
            "pid": os.getpid(),
            "started_at": now,
            "last_heartbeat": now,
            "last_cycle_ok": None,
            "open_positions": open_positions,
            "balance_actual": round(balance_actual, 2),
            "last_error": None,
            "shutdown_reason": None
        }
        self._write_state(state)

    def update_heartbeat(self, balance_actual=0.0, open_positions=0):
        state = self._read_state()
        now = self._utc_now()

        state.setdefault("started_at", now)
        state["running"] = True
        state["pid"] = os.getpid()
        state["last_heartbeat"] = now
        state["open_positions"] = open_positions
        state["balance_actual"] = round(balance_actual, 2)
        self._write_state(state)

    def mark_cycle_ok(self, balance_actual=0.0, open_positions=0):
        state = self._read_state()
        now = self._utc_now()

        state.setdefault("started_at", now)
        state["running"] = True
        state["pid"] = os.getpid()
        state["last_heartbeat"] = now
        state["last_cycle_ok"] = now
        state["open_positions"] = open_positions
        state["balance_actual"] = round(balance_actual, 2)
        state["last_error"] = None
        self._write_state(state)

    def mark_error(self, error_message, balance_actual=0.0, open_positions=0):
        state = self._read_state()
        now = self._utc_now()

        state.setdefault("started_at", now)
        state["running"] = True
        state["pid"] = os.getpid()
        state["last_heartbeat"] = now
        state["open_positions"] = open_positions
        state["balance_actual"] = round(balance_actual, 2)
        state["last_error"] = str(error_message)
        self._write_state(state)

    def mark_stopped(self, reason="STOPPED", balance_actual=0.0, open_positions=0):
        state = self._read_state()
        now = self._utc_now()

        state.setdefault("started_at", now)
        state["running"] = False
        state["pid"] = os.getpid()
        state["last_heartbeat"] = now
        state["open_positions"] = open_positions
        state["balance_actual"] = round(balance_actual, 2)
        state["shutdown_reason"] = reason
        self._write_state(state)

    def read_current_state(self):
        return self._read_state()