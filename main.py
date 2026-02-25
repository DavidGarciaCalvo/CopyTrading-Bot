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

def imprimir_bienvenida():
    print("=" * 50)
    print("🚀 SISTEMA DE COPY TRADING HÍBRIDO (SOLANA-BINANCE)")
    print("=" * 50)
    print(f"📡 Vigilando Wallets: {len(Config.WALLETS_TO_TRACK)} ballenas configuradas")
    print(f"💰 Capital Inicial: {Config.INITIAL_CAPITAL} {Config.BASE_CURRENCY}")
    print(f"🛡️  Riesgo por Trade: {Config.MAX_RISK_PER_TRADE * 100}%")
    print("-" * 50)

def main():
    # 1. Inicialización de componentes
    try:
        signal_provider = SignalProvider()
        gestor = PortfolioManager()
    except Exception as e:
        print(f"❌ Error al inicializar componentes: {e}")
        return

    imprimir_bienvenida()

    # --- PRUEBA INICIAL (MOCK) ---
    # Esto verifica que la BD y Telegram funcionan antes de empezar el radar
    print("🧪 Ejecutando señal de prueba...")
    señales_mock = signal_provider.get_signal(mock=True)
    for s in señales_mock:
        precio_test = obtener_precio_binance(s['asset'])
        if precio_test:
            gestor.abrir_posicion(s['asset'], precio_test, signature="MOCK_TEST")
    # -----------------------------

    print("\n🕵️ Radar iniciado. Buscando movimientos en la blockchain...")
    
    while True:
        try:
            # 2. RASTREO: Consultamos si alguna ballena ha operado
            # get_signal() ahora nos devuelve una lista de diccionarios con 'label'
            nuevas_señales = signal_provider.get_signal()

            if nuevas_señales:
                for señal in nuevas_señales:
                    asset = señal['asset']
                    perfil = señal['label']  # Extraemos la etiqueta (SMART_MONEY, TRENDING, etc.)
                    
                    print(f"\n🔔 [NUEVA SEÑAL - {perfil}]: {asset} detectada!")
                    
                    # 3. EJECUCIÓN: Obtenemos precio real y abrimos posición
                    precio_mercado = obtener_precio_binance(asset)
                    
                    if precio_mercado:
                        # IMPORTANTE: Pasamos el 'perfil' (label) al gestor para que aparezca en Telegram
                        gestor.abrir_posicion(
                            asset=asset, 
                            precio_mercado=precio_mercado, 
                            signature=señal['signature'],
                            label=perfil  # <--- Esto envía la etiqueta al gestor
                        )
                    else:
                        print(f"⚠️ No se pudo obtener precio para {asset} en Binance. Abortando.")
                        
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
            print("\n🛑 Bot detenido manualmente por el usuario.")
            break
        except Exception as e:
            print(f"\n⚠️ Error en el bucle principal: {e}")
            time.sleep(10) # Espera antes de reintentar

if __name__ == "__main__":
    main()