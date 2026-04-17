from poc_jupiter_perps import JupiterPerpsDetectorPOC
from follower_interpreter import interpretar_senal_para_follower

detector = JupiterPerpsDetectorPOC("dummy_wallet")

before = {
    "WBTC": {"side": "long", "size_value": 1300}
}
after = {
    "WBTC": {"side": "long", "size_value": 1000}
}

cambios = detector.clasificar_cambios(before, after)

senales = []
for mercado, info in cambios.items():
    senal = detector.traducir_evento_a_senal(
        info["event"],
        mercado,
        info["before"],
        info["after"],
    )
    if senal:
        senales.append(senal)

follower_position = {"side": "long", "size_value": 500}

print("=== PIPELINE TEST ===")
print("Cambios:", cambios)
print("Señales:", senales)

for senal in senales:
    accion = interpretar_senal_para_follower(senal, follower_position)
    print("Acción follower:", accion)

print("=== FIN PIPELINE TEST ===")