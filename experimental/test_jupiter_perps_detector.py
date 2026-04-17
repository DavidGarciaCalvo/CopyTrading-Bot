from poc_jupiter_perps import JupiterPerpsDetectorPOC

detector = JupiterPerpsDetectorPOC("dummy_wallet")

casos = [
    (
        "OPEN_LONG",
        None,
        {"side": "long", "size_value": 1000}
    ),
    (
        "OPEN_SHORT",
        None,
        {"side": "short", "size_value": 1000}
    ),
    (
        "INCREASE_LONG",
        {"side": "long", "size_value": 1000},
        {"side": "long", "size_value": 1300}
    ),
    (
        "REDUCE_LONG",
        {"side": "long", "size_value": 1300},
        {"side": "long", "size_value": 1000}
    ),
    (
        "CLOSE_LONG",
        {"side": "long", "size_value": 1000},
        None
    ),
    (
        "FLIP_LONG_TO_SHORT",
        {"side": "long", "size_value": 1000},
        {"side": "short", "size_value": 900}
    ),
    (
        "NO_CHANGE",
        {"side": "long", "size_value": 1000},
        {"side": "long", "size_value": 1000.4}
    ),
]

print("=== TESTS clasificar_evento ===")

for i, (esperado, before, after) in enumerate(casos, start=1):
    obtenido = detector.clasificar_evento(before, after)
    ok = "OK" if obtenido == esperado else "FAIL"

    print(f"\nCaso {i}")
    print(f"Esperado: {esperado}")
    print(f"Obtenido: {obtenido}")
    print(f"Resultado: {ok}")

print("\n=== FIN TESTS ===")