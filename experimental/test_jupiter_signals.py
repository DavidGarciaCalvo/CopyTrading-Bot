from poc_jupiter_perps import JupiterPerpsDetectorPOC

detector = JupiterPerpsDetectorPOC("dummy_wallet")

casos = [
    (
        "OPEN_LONG",
        "WBTC",
        None,
        {"side": "long", "size_value": 1000},
        {
            "signal_type": "OPEN_LONG",
            "leader_side_before": None,
            "leader_side_after": "long",
            "size_before_usd": 0,
            "size_after_usd": 1000,
            "size_delta_usd": 1000,
        }
    ),
    (
        "REDUCE_LONG",
        "WBTC",
        {"side": "long", "size_value": 1300},
        {"side": "long", "size_value": 1000},
        {
            "signal_type": "REDUCE_LONG",
            "leader_side_before": "long",
            "leader_side_after": "long",
            "size_before_usd": 1300,
            "size_after_usd": 1000,
            "size_delta_usd": -300,
        }
    ),
    (
        "FLIP_LONG_TO_SHORT",
        "WBTC",
        {"side": "long", "size_value": 1000},
        {"side": "short", "size_value": 900},
        {
            "signal_type": "FLIP_LONG_TO_SHORT",
            "leader_side_before": "long",
            "leader_side_after": "short",
            "size_before_usd": 1000,
            "size_after_usd": 900,
            "size_delta_usd": -100,
        }
    ),
    (
        "NO_CHANGE",
        "WBTC",
        {"side": "long", "size_value": 1000},
        {"side": "long", "size_value": 1000},
        None
    ),
]

print("=== TESTS traducir_evento_a_senal ===")

for i, (evento, symbol, before, after, esperado) in enumerate(casos, start=1):
    obtenido = detector.traducir_evento_a_senal(evento, symbol, before, after)

    print(f"\nCaso {i}")
    print(f"Evento: {evento}")
    print(f"Señal obtenida: {obtenido}")

    if esperado is None:
        ok = obtenido is None
    else:
        ok = (
            obtenido is not None
            and obtenido["signal_type"] == esperado["signal_type"]
            and obtenido["leader_side_before"] == esperado["leader_side_before"]
            and obtenido["leader_side_after"] == esperado["leader_side_after"]
            and obtenido["size_before_usd"] == esperado["size_before_usd"]
            and obtenido["size_after_usd"] == esperado["size_after_usd"]
            and obtenido["size_delta_usd"] == esperado["size_delta_usd"]
            and obtenido["asset"] == f"{symbol}/USDT"
            and obtenido["market"] == symbol
            and obtenido["provider"] == "jupiter_perps"
        )

    print(f"Resultado: {'OK' if ok else 'FAIL'}")

print("\n=== FIN TESTS ===")