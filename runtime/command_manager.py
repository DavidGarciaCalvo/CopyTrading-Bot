import json
import os
from datetime import datetime, UTC


class RuntimeCommandManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.runtime_dir = os.path.join(base_dir, "runtime")
        self.commands_file = os.path.join(self.runtime_dir, "commands.json")
        self._ensure_runtime_dir()
        self._ensure_commands_file()

    def _ensure_runtime_dir(self):
        os.makedirs(self.runtime_dir, exist_ok=True)

    def _ensure_commands_file(self):
        if not os.path.exists(self.commands_file):
            with open(self.commands_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)

    def _utc_now(self):
        return datetime.now(UTC).isoformat()

    def _read_commands(self):
        try:
            with open(self.commands_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_commands(self, commands):
        with open(self.commands_file, "w", encoding="utf-8") as f:
            json.dump(commands, f, indent=2, ensure_ascii=False)

    def get_pending_commands(self):
        commands = self._read_commands()
        return [cmd for cmd in commands if cmd.get("status") == "pending"]

    def mark_done(self, command_id, result_message=None):
        commands = self._read_commands()
        for cmd in commands:
            if cmd.get("id") == command_id:
                cmd["status"] = "done"
                cmd["processed_at"] = self._utc_now()
                cmd["result"] = result_message
                break
        self._write_commands(commands)

    def mark_failed(self, command_id, error_message=None):
        commands = self._read_commands()
        for cmd in commands:
            if cmd.get("id") == command_id:
                cmd["status"] = "failed"
                cmd["processed_at"] = self._utc_now()
                cmd["result"] = str(error_message) if error_message else "Unknown error"
                break
        self._write_commands(commands)

    def add_command(self, action, payload=None):
        commands = self._read_commands()

        new_id = f"cmd_{len(commands) + 1:04d}"
        new_command = {
            "id": new_id,
            "action": action,
            "payload": payload or {},
            "status": "pending",
            "created_at": self._utc_now()
        }

        commands.append(new_command)
        self._write_commands(commands)
        return new_command