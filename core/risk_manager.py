from config import Config

class RiskManager:
    def __init__(self):
        self.risk_per_trade = Config.MAX_RISK_PER_TRADE
        self.stop_loss_pct = Config.STOP_LOSS_PCT
        self.take_profit_pct = Config.TAKE_PROFIT_PCT

    def calcular_entrada(self, balance_total, precio_entrada):
        """
        Calcula el tamaño de la posición y los niveles de SL/TP.
        """
        cantidad_usdt = balance_total * self.risk_per_trade
        sl = precio_entrada * (1 - self.stop_loss_pct)
        tp = precio_entrada * (1 + self.take_profit_pct)
        return cantidad_usdt, sl, tp

    def validar_operacion(self, balance_disponible, cantidad_usdt):
        """
        Verifica si la operación es segura y viable.
        """
        if cantidad_usdt > balance_disponible:
            return False, "Saldo insuficiente"
        if cantidad_usdt <= 0:
            return False, "Monto de inversión inválido"
        return True, "OK"
