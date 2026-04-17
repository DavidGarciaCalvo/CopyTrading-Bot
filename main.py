# Archivo principal del bot. Este script es el punto de entrada para ejecutar el bot en modo simulado.
# Aquí se inicializan los componentes principales: el proveedor de señales simulado, el gestor de riesgos 
# y el gestor de portafolio. El bot escucha las señales generadas por el proveedor simulado, consulta al 
# gestor de riesgos para determinar si la operación es viable y, si es así, registra la compra en el 
# portafolio y guarda la operación en la base de datos. Al finalizar la ejecución, se imprime un resumen de 
# las operaciones realizadas. Este archivo es esencial para probar la integración de todos los módulos y 
# validar la lógica del bot antes de una posible integración con un exchange real. En futuras iteraciones, 
# se podrían agregar funcionalidades adicionales como la gestión de ventas, stop-loss, take-profit, entre 
# otras. 

import time
import sys
from config import Config
from core.signal_provider import SignalProvider
from core.portfolio_manager import PortfolioManager
from utils.price_service import obtener_precio_binance
from experimental.perps_signal_service import (
    procesar_senales_perps,
    traducir_follower_action_a_side
)


def imprimir_bienvenida(balance_actual):
    print("=" * 50)
    print("🚀 SISTEMA DE COPY TRADING HÍBRIDO (SOLANA-BINANCE)")
    print("=" * 50)
    print(f"📡 Vigilando Wallets: {len(Config.WALLETS_TO_TRACK)} ballenas configuradas")
    print(f"💰 Balance Actual de la Cuenta: {balance_actual:.2f} {Config.BASE_CURRENCY}")
    print(f"⚠️  Riesgo por Trade: {Config.MAX_RISK_PER_TRADE * 100}%")
    print("-" * 50)


def construir_follower_positions_by_market(posiciones):
    """
    Convierte las posiciones actuales del follower desde formato asset
    (ej. WBTC/USDT) a formato market (ej. WBTC), para que el módulo
    de perps pueda consultar el contexto actual del follower.
    """
    resultado = {}

    for asset, data in posiciones.items():
        market = asset.replace("/USDT", "")
        side_actual = data.get("side", "LONG")

        if side_actual == "LONG":
            side_normalizada = "long"
        elif side_actual == "SHORT":
            side_normalizada = "short"
        else:
            continue

        resultado[market] = {
            "side": side_normalizada,
            "asset": asset,
            "raw": data
        }

    return resultado


def main():
    # 1. Inicialización de componentes
    try:
        signal_provider = SignalProvider()
        gestor = PortfolioManager()
    except Exception as e:
        print(f"❌ Error al inicializar componentes: {e}")
        return

    imprimir_bienvenida(gestor.balance_actual)

    print("\n🕵️ Radar iniciado. Buscando movimientos en la blockchain...")
    
    while True:
        try:
            # 2. RASTREO: Consultamos si alguna ballena ha operado
            # get_signal() ahora nos devuelve una lista de diccionarios con 'label'
            nuevas_señales = signal_provider.get_signal()

            if nuevas_señales:
                for señal in nuevas_señales:
                    asset = señal["asset"]
                    perfil = señal["label"]  # Extraemos la etiqueta (SMART_MONEY, TRENDING, etc.)
                    
                    print(f"\n🔔 [NUEVA SEÑAL - {perfil}]: {asset} detectada!")
                    
                    # 3. EJECUCIÓN SPOT: Obtenemos precio real y abrimos/cerramos posición
                    precio_mercado = obtener_precio_binance(asset)
                    
                    if precio_mercado:
                        gestor.procesar_señal(
                            asset=asset,
                            precio_mercado=precio_mercado,
                            side=señal.get("side", "LONG"),
                            signature=señal["signature"],
                            label=perfil
                        )
                    else:
                        print(f"⚠️ No se pudo obtener precio para {asset} en Binance. Abortando.")

            # 3B. PERPS: procesamos señales detectadas en Jupiter Perps
            follower_positions_by_market = construir_follower_positions_by_market(gestor.posiciones)

            resultados_perps = procesar_senales_perps(
                wallet="HhZw63SHGfpAhdZLNTzfkNhwxPDrzPSAQM7ikDvXjqco",
                follower_positions_by_market=follower_positions_by_market
            )

            if resultados_perps:
                for resultado in resultados_perps:
                    signal = resultado["signal"]
                    follower_action = resultado["follower_action"]
                    side_traducida = traducir_follower_action_a_side(follower_action)

                    if side_traducida is None:
                        print(
                            f"\n⚪ [PERPS] Señal detectada pero no ejecutable todavía: "
                            f"{signal['signal_type']} en {signal['asset']} "
                            f"(acción follower: {follower_action})"
                        )
                        continue

                    asset = signal["asset"]

                    print(
                        f"\n🟣 [SEÑAL PERPS]: {signal['signal_type']} en {asset} "
                        f"→ acción follower: {follower_action}"
                    )

                    precio_mercado = obtener_precio_binance(asset)

                    if not precio_mercado:
                        print(f"⚠️ No se pudo obtener precio para {asset} en Binance. Abortando.")
                        continue

                    if side_traducida == "CLOSE":
                        if asset in gestor.posiciones:
                            gestor.cerrar_posicion(
                                asset=asset,
                                precio_mercado=precio_mercado,
                                label="JUPITER_PERPS",
                                motivo="PERPS_CLOSE_SIGNAL"
                            )
                        else:
                            print(f"⚪ [PERPS] No hay posición abierta en {asset} que cerrar.")
                    else:
                        gestor.procesar_señal(
                            asset=asset,
                            precio_mercado=precio_mercado,
                            side=side_traducida,
                            signature=f"PERPS_{signal['signal_type']}",
                            label="JUPITER_PERPS"
                        )
                        
            # 4. MONITORIZACIÓN: Revisamos salidas (SL/TP) de las posiciones abiertas
            # Obtenemos precios actualizados para todo lo que tenemos en cartera
            activos_en_cartera = list(gestor.posiciones.keys())
            if activos_en_cartera:
                precios_vivos = {}
                for activo in activos_en_cartera:
                    p = obtener_precio_binance(activo)
                    if p:
                        precios_vivos[activo] = p
                
                # El gestor decide si cerrar según los límites
                gestor.gestionar_salidas(precios_vivos)

            # 5. DESCANSO: Evitamos saturar las APIs (Helius/Binance)
            # Imprimimos un punto cada ciclo para saber que el bot sigue vivo
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(Config.POLLING_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n⏸️ Bot pausado temporalmente.")
            abiertas = list(gestor.posiciones.keys())
            if abiertas:
                print(f"📦 Posiciones abiertas: {', '.join(abiertas)}")
                comando = input("👉 Escribe el activo a cerrar, 'CLOSEALL' para cerrar todas y salir, 'exit' para apagar, o Enter: ").strip().upper()
                
                if comando == "EXIT":
                    print("🛑 Apagando el bot...")
                    break
                elif comando == "CLOSEALL":
                    print("🛑 Cerrando TODAS las posiciones...")
                    for activo in list(gestor.posiciones.keys()):
                        precio = obtener_precio_binance(activo)
                        if precio:
                            gestor.cerrar_posicion(activo, precio, label="MANUAL", motivo="CIERRE MANUAL")
                        else:
                            print(f"⚠️ No se pudo obtener el precio para {activo}. Se queda abierta.")
                    print("🛑 Apagando el bot...")
                    break
                elif comando in gestor.posiciones:
                    precio = obtener_precio_binance(comando)
                    if precio:
                        gestor.cerrar_posicion(comando, precio, label="MANUAL", motivo="CIERRE MANUAL")
                    else:
                        print(f"⚠️ No se pudo obtener el precio actual para {comando}.")
                        
                    # Preguntamos si desea salir después de cerrar una operación específica
                    sub_comando = input("👉 ¿Deseas apagar el bot ahora? (S/N): ").strip().upper()
                    if sub_comando == "S" or sub_comando == "Y":
                        print("🛑 Apagando el bot...")
                        break
                    else:
                        print("▶️ Reanudando radar...")
                else:
                    print("▶️ Reanudando radar...")
            else:
                comando = input("👉 No hay posiciones abiertas. Escribe 'exit' para apagar, o Enter para reanudar: ").strip().lower()
                if comando == "exit":
                    print("🛑 Apagando el bot...")
                    break
                print("▶️ Reanudando radar...")
        except Exception as e:
            print(f"\n⚠️ Error en el bucle principal: {e}")
            time.sleep(10)  # Espera antes de reintentar


if __name__ == "__main__":
    main()