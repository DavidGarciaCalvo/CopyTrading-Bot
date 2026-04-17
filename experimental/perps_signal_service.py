from experimental.poc_jupiter_perps import JupiterPerpsDetectorPOC
from experimental.follower_interpreter import interpretar_senal_para_follower


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


def traducir_follower_action_a_side(follower_action):
    """
    Traduce la acción contextual del follower a una side compatible con
    PortfolioManager.procesar_señal().

    Devuelve:
    - "LONG"
    - "SHORT"
    - "CLOSE"
    - None  -> no hacer nada / no soportado todavía
    """
    mapping = {
        "OPEN_LONG": "LONG",
        "OPEN_SHORT": "SHORT",
        "CLOSE_LONG_AND_OPEN_SHORT": "SHORT",
        "CLOSE_SHORT_AND_OPEN_LONG": "LONG",
        "CLOSE_LONG": "CLOSE",
        "CLOSE_SHORT": "CLOSE",
    }

    return mapping.get(follower_action)