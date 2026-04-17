from follower_interpreter import interpretar_senal_para_follower

casos = [
    # follower flat
    (
        "flat + OPEN_LONG",
        {"signal_type": "OPEN_LONG"},
        None,
        "OPEN_LONG",
    ),
    (
        "flat + OPEN_SHORT",
        {"signal_type": "OPEN_SHORT"},
        None,
        "OPEN_SHORT",
    ),
    (
        "flat + CLOSE_LONG",
        {"signal_type": "CLOSE_LONG"},
        None,
        "NO_ACTION",
    ),
    (
        "flat + REDUCE_SHORT",
        {"signal_type": "REDUCE_SHORT"},
        None,
        "NO_ACTION",
    ),

    # follower long
    (
        "long + INCREASE_LONG",
        {"signal_type": "INCREASE_LONG"},
        {"side": "long"},
        "INCREASE_LONG",
    ),
    (
        "long + REDUCE_LONG",
        {"signal_type": "REDUCE_LONG"},
        {"side": "long"},
        "REDUCE_LONG",
    ),
    (
        "long + CLOSE_LONG",
        {"signal_type": "CLOSE_LONG"},
        {"side": "long"},
        "CLOSE_LONG",
    ),
    (
        "long + OPEN_SHORT",
        {"signal_type": "OPEN_SHORT"},
        {"side": "long"},
        "CLOSE_LONG_AND_OPEN_SHORT",
    ),

    # follower short
    (
        "short + INCREASE_SHORT",
        {"signal_type": "INCREASE_SHORT"},
        {"side": "short"},
        "INCREASE_SHORT",
    ),
    (
        "short + REDUCE_SHORT",
        {"signal_type": "REDUCE_SHORT"},
        {"side": "short"},
        "REDUCE_SHORT",
    ),
    (
        "short + CLOSE_SHORT",
        {"signal_type": "CLOSE_SHORT"},
        {"side": "short"},
        "CLOSE_SHORT",
    ),
    (
        "short + OPEN_LONG",
        {"signal_type": "OPEN_LONG"},
        {"side": "short"},
        "CLOSE_SHORT_AND_OPEN_LONG",
    ),
]

print("=== TESTS interpretar_senal_para_follower ===")

for i, (nombre, signal, follower_position, esperado) in enumerate(casos, start=1):
    obtenido = interpretar_senal_para_follower(signal, follower_position)
    ok = "OK" if obtenido == esperado else "FAIL"

    print(f"\nCaso {i}: {nombre}")
    print(f"Esperado: {esperado}")
    print(f"Obtenido: {obtenido}")
    print(f"Resultado: {ok}")

print("\n=== FIN TESTS ===")