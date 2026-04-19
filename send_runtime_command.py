import sys
from runtime.command_manager import RuntimeCommandManager


def main():
    if len(sys.argv) < 2:
        print("Uso: python send_runtime_command.py <stop|closeall>")
        return

    action = sys.argv[1].strip().lower()
    manager = RuntimeCommandManager()

    command = manager.add_command(action=action)
    print(f"✅ Comando creado: {command}")


if __name__ == "__main__":
    main()