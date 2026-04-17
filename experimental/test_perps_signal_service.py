from perps_signal_service import procesar_senales_perps


# Simulación de posiciones actuales del follower
follower_positions_by_market = {
    "WBTC": {"side": "long", "size_value": 500}
}

resultados = procesar_senales_perps(
    wallet="HhZw63SHGfpAhdZLNTzfkNhwxPDrzPSAQM7ikDvXjqco",
    follower_positions_by_market=follower_positions_by_market,
)

print("=== TEST perps_signal_service ===")

if not resultados:
    print("No hay señales nuevas.")
else:
    for r in resultados:
        print("\nMercado:", r["market"])
        print("Signal:", r["signal"])
        print("Follower position:", r["follower_position"])
        print("Follower action:", r["follower_action"])

print("\n=== FIN TEST ===")