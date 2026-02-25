from config import Config
from database.db import Session, Operacion, inicializar_db
from datetime import datetime
from utils.notifier import TelegramNotifier
from core.risk_manager import RiskManager
import os

class PortfolioManager:
    def __init__(self):
        inicializar_db()
        self.nombre_archivo = "balance_acumulado.txt" # Guardamos el nombre
        
        # --- MEJORA: CARGA Y CREACIÓN INICIAL ---
        if not os.path.exists(self.nombre_archivo):
            with open(self.nombre_archivo, "w") as f:
                f.write(f"{Config.INITIAL_CAPITAL:.2f}")
        
        self.balance_actual = self.cargar_balance_persistente()
        # ----------------------------------------
        
        self.risk_manager = RiskManager()
        self.posiciones = {} 
        self.notifier = TelegramNotifier()
        print(f"🏦 Sistema iniciado. Balance actual: {self.balance_actual:.2f} USDT")

    def cargar_balance_persistente(self):
        """Lee el último balance guardado o usa el inicial de Config."""
        nombre_archivo = "balance_acumulado.txt"
        if os.path.exists(nombre_archivo):
            try:
                with open(nombre_archivo, "r") as f:
                    contenido = f.read().strip()
                    if contenido:
                        return float(contenido)
            except Exception as e:
                print(f"⚠️ Error leyendo archivo de balance: {e}")
        
        # Si no existe el archivo o está vacío, usa el de Config
        return Config.INITIAL_CAPITAL

    def guardar_balance_persistente(self):
        """Guarda el balance actual en un archivo físico."""
        try:
            with open("balance_acumulado.txt", "w") as f:
                f.write(f"{self.balance_actual:.2f}")
        except Exception as e:
            print(f"⚠️ Error guardando balance en archivo: {e}")

    def abrir_posicion(self, asset, precio_mercado, signature="MOCK_SIG", label="UNKNOWN"):
        """
        Calcula el volumen dinámico, aplica el slippage y guarda la 
        operación en la base de datos.
        """
        # 1. AJUSTE DE REALISMO (Slippage)
        precio_entrada = precio_mercado * (1 + Config.EXPECTED_SLIPPAGE)
        
        # 2. CÁLCULO DE RIESGO (Delegado al RiskManager)
        cantidad_usdt, sl, tp = self.risk_manager.calcular_entrada(self.balance_actual, precio_entrada)
        
        # 3. VALIDACIÓN
        es_valida, motivo = self.risk_manager.validar_operacion(self.balance_actual, cantidad_usdt)
        if not es_valida:
            print(f"⚠️ Operación cancelada: {motivo}")
            return

        # 4. GUARDADO EN MEMORIA
        self.posiciones[asset] = {
            "entrada": precio_entrada,
            "cantidad": cantidad_usdt,
            "sl": sl,
            "tp": tp,
            "signature": signature
        }
        
        # 5. PERSISTENCIA EN BASE DE DATOS
        try:
            session = Session()
            nueva_op = Operacion(
                asset=asset,
                precio_entrada=precio_entrada,
                cantidad_usdt=cantidad_usdt,
                sl=sl,
                tp=tp,
                status="OPEN",
                signature_solana=signature
            )
            session.add(nueva_op)
            session.commit()
            session.close()
        except Exception as e:
            print(f"⚠️ Error al guardar en BD: {e}")

        # 6. FEEDBACK EN CONSOLA
        print(f"\n🚀 [ORDEN EJECUTADA] {asset}")
        print(f"   Balance disponible: {self.balance_actual:.2f} USDT")
        print(f"   Inversión ({(Config.MAX_RISK_PER_TRADE*100)}%): {cantidad_usdt:.2f} USDT")
        print(f"   Precio API: {precio_mercado:.4f}")
        print(f"   Precio con Slippage: {precio_entrada:.4f}")
        print(f"   🛡️ SL: {sl:.4f} | 🎯 TP: {tp:.4f}")

        # 7. Envío de notificación
        msg = (
            f"🚀 *ORDEN EJECUTADA*\n\n"
            f"👤 *Perfil:* {label}\n"
            f"📦 *Activo:* {asset}\n"
            f"💰 *Precio Entrada:* {precio_entrada:.4f}\n"
            f"🛡️ * SL:* {sl:.4f} | 🎯 *TP:* {tp:.4f}\n"
            f"💵 *Inversión:* {cantidad_usdt:.2f} USDT"
        )
        self.notifier.enviar_mensaje(msg)

    def gestionar_salidas(self, precios_actuales):
        """
        Vigila las posiciones abiertas y las cierra si tocan SL o TP.
        """
        for asset, data in list(self.posiciones.items()):
            precio_hoy = precios_actuales.get(asset)
            if not precio_hoy:
                continue

            toca_sl = precio_hoy <= data['sl']
            toca_tp = precio_hoy >= data['tp']

            if toca_sl or toca_tp:
                resultado_str = "CLOSED_TP" if toca_tp else "CLOSED_SL"
                
                # 1. CÁLCULO FINANCIERO
                variacion = (precio_hoy / data['entrada']) - 1
                beneficio_neto = data['cantidad'] * variacion
                
                # Actualizamos el balance en memoria
                self.balance_actual += beneficio_neto
                
                # --- NUEVO: GUARDAR BALANCE CADA VEZ QUE CERRAMOS ---
                self.guardar_balance_persistente()
                # ----------------------------------------------------
                
                # 2. ACTUALIZAR BASE DE DATOS
                try:
                    session = Session()
                    op_db = session.query(Operacion).filter_by(asset=asset, status="OPEN").first()
                    if op_db:
                        op_db.status = resultado_str
                        op_db.fecha_cierre = datetime.utcnow()
                        op_db.resultado_neto = beneficio_neto
                        session.commit()
                    session.close()
                except Exception as e:
                    print(f"⚠️ Error al actualizar BD en cierre: {e}")

                # 3. NOTIFICACIÓN TELEGRAM
                emoji = "✅" if toca_tp else "🛑"
                # Incluimos el .replace('_', ' ') para evitar errores de negrita
                msg_cierre = (
                    f"{emoji} *POSICIÓN CERRADA*\n\n"
                    f"📦 *Activo:* {asset}\n"
                    f"📊 *Motivo:* {resultado_str.replace('_', ' ')}\n"
                    f"💰 *Precio Cierre:* {precio_hoy:.4f}\n"
                    f"💸 *Resultado:* {beneficio_neto:.2f} USDT\n"
                    f"🏦 *Balance Total:* {self.balance_actual:.2f} USDT"
                )
                self.notifier.enviar_mensaje(msg_cierre)

                # 4. FEEDBACK EN CONSOLA
                print(f"\n💰 [CIERRE {resultado_str}] en {asset}")
                print(f"   Resultado: {beneficio_neto:.2f} USDT")
                print(f"   Balance Guardado: {self.balance_actual:.2f} USDT")
                
                del self.posiciones[asset]