from poc_jupiter_perps import JupiterPerpsDetectorPOC
from follower_interpreter import interpretar_senal_para_follower


def procesar_senales_perps(wallet, follower_positions_by_market):
    """
    Procesa señales de Jupiter Perps para una wallet líder y devuelve,
    por cada mercado, la acción sugerida para el follower en función
    de su posición actual.
    """
    detector = JupiterPerpsDetectorPOC(wallet)
    signals = detector.obtener_senales()

    resultados = []

    for signal in signals:
        market = signal["market"]
        follower_position = follower_positions_by_market.get(market)

        follower_action = interpretar_senal_para_follower(signal, follower_position)

        resultados.append({
            "market": market,
            "signal": signal,
            "follower_position": follower_position,
            "follower_action": follower_action,
        })

    return resultados