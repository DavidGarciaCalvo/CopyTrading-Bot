import json
import os
import requests
from datetime import datetime, UTC

WALLET = "HhZw63SHGfpAhdZLNTzfkNhwxPDrzPSAQM7ikDvXjqco"
SNAPSHOT_FILE = "experimental/jupiter_snapshot.json"


class JupiterPerpsDetectorPOC:
    def __init__(self, wallet):
        self.wallet = wallet

    def obtener_respuesta_cruda(self):
        url = f"https://api.jup.ag/portfolio/v1/positions/{self.wallet}"

        try:
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                print(f"❌ Error API Jupiter: {response.status_code}")
                print(response.text)
                return None

            return response.json()

        except Exception as e:
            print(f"❌ Error consultando Jupiter: {e}")
            return None

    def extraer_posiciones_limpias(self, data):
        posiciones = {}

        if not data:
            return posiciones

        elements = data.get("elements", [])
        token_info = data.get("tokenInfo", {}).get("solana", {})

        for element in elements:
            if element.get("type") != "leverage":
                continue

            leverage_data = element.get("data", {})
            isolated = leverage_data.get("isolated", {})
            positions = isolated.get("positions", [])

            for pos in positions:
                token_address = pos.get("address")
                token_meta = token_info.get(token_address, {})
                symbol = token_meta.get("symbol", token_address)

                posiciones[symbol] = {
                    "side": pos.get("side"),
                    "size": pos.get("size", 0),
                    "size_value": pos.get("sizeValue", 0),
                    "entry_price": pos.get("entryPrice", 0),
                    "mark_price": pos.get("markPrice", 0),
                    "pnl_value": pos.get("pnlValue", 0),
                    "liquidation_price": pos.get("liquidationPrice", 0),
                }

        return posiciones

    def guardar_snapshot(self, posiciones):
        payload = {
            "wallet": self.wallet,
            "timestamp": datetime.now(UTC).isoformat(),
            "positions": posiciones,
        }

        with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"📸 Snapshot guardado en {SNAPSHOT_FILE}")

    def cargar_snapshot(self):
        if not os.path.exists(SNAPSHOT_FILE):
            return {}

        try:
            with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("positions", {})
        except Exception as e:
            print(f"⚠️ Error cargando snapshot: {e}")
            return {}

    def clasificar_evento(self, before_pos, after_pos):
        if before_pos is None and after_pos is None:
            return "NO_CHANGE"

        if before_pos is None and after_pos is not None:
            return "OPEN_LONG" if after_pos["side"] == "long" else "OPEN_SHORT"

        if before_pos is not None and after_pos is None:
            return "CLOSE_LONG" if before_pos["side"] == "long" else "CLOSE_SHORT"

        before_side = before_pos["side"]
        after_side = after_pos["side"]
        before_size = before_pos.get("size_value", 0)
        after_size = after_pos.get("size_value", 0)

        if before_side == after_side:
            if abs(after_size - before_size) < 1e-9:
                return "NO_CHANGE"

            if after_size > before_size:
                return "INCREASE_LONG" if after_side == "long" else "INCREASE_SHORT"

            if after_size < before_size:
                return "REDUCE_LONG" if after_side == "long" else "REDUCE_SHORT"

        if before_side == "long" and after_side == "short":
            return "FLIP_LONG_TO_SHORT"

        if before_side == "short" and after_side == "long":
            return "FLIP_SHORT_TO_LONG"

        return "UNKNOWN_STATE"

    def clasificar_cambios(self, posiciones_antes, posiciones_despues):
        resultados = {}

        mercados = sorted(set(posiciones_antes.keys()) | set(posiciones_despues.keys()))

        for mercado in mercados:
            before_pos = posiciones_antes.get(mercado)
            after_pos = posiciones_despues.get(mercado)
            evento = self.clasificar_evento(before_pos, after_pos)

            resultados[mercado] = {
                "before": before_pos,
                "after": after_pos,
                "event": evento,
            }

        return resultados

    def traducir_evento_a_senal(self, evento, symbol):
        bullish = {
            "OPEN_LONG",
            "INCREASE_LONG",
            "REDUCE_SHORT",
            "CLOSE_SHORT",
            "FLIP_SHORT_TO_LONG",
        }

        bearish = {
            "OPEN_SHORT",
            "INCREASE_SHORT",
            "REDUCE_LONG",
            "CLOSE_LONG",
            "FLIP_LONG_TO_SHORT",
        }

        if evento in bullish:
            return {
                "asset": f"{symbol}/USDT",
                "side": "LONG",
                "action": "ABRIR_COMPRA_O_MANTENER_LONG",
            }

        if evento in bearish:
            return {
                "asset": f"{symbol}/USDT",
                "side": "SHORT",
                "action": "CERRAR_LONG_SI_EXISTE_O_SESGO_BAJISTA",
            }

        return {
            "asset": f"{symbol}/USDT",
            "side": None,
            "action": "NO_HACER_NADA",
        }


def imprimir_posiciones(posiciones, titulo):
    print(f"\n📊 {titulo}")
    if not posiciones:
        print("   (sin posiciones)")
        return

    for symbol, pos in posiciones.items():
        print(
            f"   - {symbol}: side={pos['side']}, "
            f"size_value={pos['size_value']:.4f}, "
            f"entry={pos['entry_price']:.4f}, "
            f"mark={pos['mark_price']:.4f}, "
            f"pnl={pos['pnl_value']:.4f}"
        )


def imprimir_cambios_y_senales(detector, cambios):
    print("\n📈 RESULTADO DEL STATE-DIFF")
    if not cambios:
        print("   (sin cambios)")
        return

    for mercado, info in cambios.items():
        senal = detector.traducir_evento_a_senal(info["event"], mercado)

        print(f"\n   Mercado: {mercado}")
        print(f"   Evento perp:   🚨 {info['event']} 🚨")
        print(f"   Antes:         {info['before']}")
        print(f"   Después:       {info['after']}")
        print(f"   Señal simple:  {senal['side']}")
        print(f"   Acción sugerida: {senal['action']}")
        print(f"   Asset bot:     {senal['asset']}")


def main():
    print("🚀 POC Jupiter Perps - detección de posiciones y traducción a señales")

    detector = JupiterPerpsDetectorPOC(WALLET)

    posiciones_antes = detector.cargar_snapshot()
    imprimir_posiciones(posiciones_antes, "Snapshot anterior")

    data = detector.obtener_respuesta_cruda()
    posiciones_despues = detector.extraer_posiciones_limpias(data)
    imprimir_posiciones(posiciones_despues, "Posiciones actuales")

    cambios = detector.clasificar_cambios(posiciones_antes, posiciones_despues)
    imprimir_cambios_y_senales(detector, cambios)

    detector.guardar_snapshot(posiciones_despues)


if __name__ == "__main__":
    main()