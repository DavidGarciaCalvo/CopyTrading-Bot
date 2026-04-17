"""
Test manual para validar el cierre de posiciones por señal de venta (SHORT).
Simula:
1. Apertura de LONG
2. Cierre mediante señal de venta
3. Caso donde no existe posición previa
"""

from core.portfolio_manager import PortfolioManager

def main():
    gestor = PortfolioManager()

    label = "TEST_WALLET"
    asset = "SOL/USDT"

    print("\n--- PASO 1: abrir LONG manualmente ---")
    gestor.procesar_señal(
        asset=asset,
        precio_mercado=100.0,
        side="LONG",
        signature="TEST_LONG",
        label=label,
    )

    print("\nPosiciones tras abrir:")
    print(gestor.posiciones)

    print("\n--- PASO 2: enviar SELL/SHORT de la misma cartera y activo ---")
    gestor.procesar_señal(
        asset=asset,
        precio_mercado=101.0,
        side="SHORT",
        signature="TEST_SHORT",
        label=label,
    )

    print("\nPosiciones tras cerrar:")
    print(gestor.posiciones)

    print("\n--- PASO 3: probar venta sin LONG previo ---")
    gestor.procesar_señal(
        asset="BTC/USDT",
        precio_mercado=50000.0,
        side="SHORT",
        signature="TEST_SHORT_2",
        label=label,
    )

    print("\nPosiciones finales:")
    print(gestor.posiciones)

if __name__ == "__main__":
    main()