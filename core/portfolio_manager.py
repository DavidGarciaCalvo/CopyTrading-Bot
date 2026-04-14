from config import Config
from database.db import Session, Operacion, inicializar_db
from datetime import datetime
from utils.notifier import TelegramNotifier
from core.risk_manager import RiskManager
import os

class PortfolioManager:
    def __init__(self):
        inicializar_db()
        # Ruta absoluta para asegurar que siempre lee/escribe el mismo archivo en la raíz del proyecto
        self.nombre_archivo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "balance_acumulado.txt")
        
        # --- MEJORA: CARGA Y CREACIÓN INICIAL ---
        if not os.path.exists(self.nombre_archivo):
            with open(self.nombre_archivo, "w") as f:
                f.write(f"{Config.INITIAL_CAPITAL:.2f}")
        
        self.balance_actual = self.cargar_balance_persistente()
        # ----------------------------------------
        
        self.risk_manager = RiskManager()
        self.margen_en_uso = 0.0
        self.posiciones = {} 
        self.cargar_posiciones_abiertas() # Recupera operaciones "OPEN" de la BD
        self.notifier = TelegramNotifier()
        print(f"🏦 Sistema iniciado. Balance actual: {self.balance_actual:.2f} USDT")
        if self.posiciones:
            print(f"🔄 Se recuperaron {len(self.posiciones)} posiciones abiertas y {self.margen_en_uso:.2f} USDT de margen.")

    def cargar_posiciones_abiertas(self):
        """Lee la base de datos y restaura las posiciones vivas en memoria."""
        try:
            session = Session()
            operaciones_vivas = session.query(Operacion).filter_by(status="OPEN").all()
            for op in operaciones_vivas:
                self.posiciones[op.asset] = {
                    "side": getattr(op, 'side', 'LONG'),
                    "entrada": op.precio_entrada,
                    "cantidad": op.cantidad_usdt,
                    "sl": op.sl,
                    "tp": op.tp,
                    "signature": op.signature_solana
                }
                self.margen_en_uso += op.cantidad_usdt
            session.close()
        except Exception as e:
            print(f"⚠️ Error al restaurar posiciones vivas: {e}")

    def cargar_balance_persistente(self):
        """Lee el último balance guardado o usa el inicial de Config."""
        if os.path.exists(self.nombre_archivo):
            try:
                with open(self.nombre_archivo, "r") as f:
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
            with open(self.nombre_archivo, "w") as f:
                f.write(f"{self.balance_actual:.2f}")
        except Exception as e:
            print(f"⚠️ Error guardando balance en archivo: {e}")

    def procesar_señal(self, asset, precio_mercado, side="LONG", signature="MOCK_SIG", label="UNKNOWN"):
        """Decide si abrir o cerrar una posición basándose en las señales."""
        if side == "SELL": 
            side = "SHORT"
            
        if asset in self.posiciones:
            pos_actual = self.posiciones[asset]
            if pos_actual.get('side', 'LONG') != side:
                self.cerrar_posicion(asset, precio_mercado, label, motivo="CLOSED_SIGNAL")
            else:
                print(f"⚠️ Ya existe una posición {side} abierta para {asset}. Ignorando señal.")
        else:
            self.abrir_posicion(asset, precio_mercado, side, signature, label)

    def abrir_posicion(self, asset, precio_mercado, side="LONG", signature="MOCK_SIG", label="UNKNOWN"):
        """
        Calcula el volumen dinámico, aplica el slippage y guarda la 
        operación en la base de datos.
        """
        # 0. EVITAR DUPLICIDAD
        if asset in self.posiciones:
            print(f"⚠️ Ya existe una posición abierta para {asset}. Ignorando nueva señal.")
            return
            
        # 1. AJUSTE DE REALISMO (Slippage)
        if side == "LONG":
            precio_entrada = precio_mercado * (1 + Config.EXPECTED_SLIPPAGE)
        else:
            precio_entrada = precio_mercado * (1 - Config.EXPECTED_SLIPPAGE)
        
        # 2. CÁLCULO DE RIESGO (Delegado al RiskManager)
        cantidad_usdt, sl, tp = self.risk_manager.calcular_entrada(self.balance_actual, precio_entrada, side)
        
        # 3. VALIDACIÓN
        balance_disponible = self.balance_actual - self.margen_en_uso
        es_valida, motivo = self.risk_manager.validar_operacion(balance_disponible, cantidad_usdt)
        if not es_valida:
            print(f"⚠️ Operación cancelada: {motivo}")
            return

        # 4. GUARDADO EN MEMORIA
        self.posiciones[asset] = {
            "side": side,
            "entrada": precio_entrada,
            "cantidad": cantidad_usdt,
            "sl": sl,
            "tp": tp,
            "signature": signature
        }
        self.margen_en_uso += cantidad_usdt
        
        # 5. PERSISTENCIA EN BASE DE DATOS
        try:
            session = Session()
            nueva_op = Operacion(
                asset=asset,
                side=side,
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
        print(f"\n🚀 [NUEVA ORDEN {side}] {asset}")
        print(f"   Balance disponible: {(self.balance_actual - self.margen_en_uso):.2f} USDT")
        print(f"   Inversión ({(Config.MAX_RISK_PER_TRADE*100)}%): {cantidad_usdt:.2f} USDT")
        print(f"   Precio API: {precio_mercado:.4f}")
        print(f"   Precio con Slippage: {precio_entrada:.4f}")
        print(f"   🛡️ SL: {sl:.4f} | 🎯 TP: {tp:.4f}")

        # 7. Envío de notificación
        msg = (
            f"🚀 *NUEVA POSICIÓN: {side}*\n\n"
            f"👤 *Perfil:* {label}\n"
            f"📦 *Activo:* {asset}\n"
            f"💰 *Precio Entrada:* {precio_entrada:.4f}\n"
            f"🛡️ * SL:* {sl:.4f} | 🎯 *TP:* {tp:.4f}\n"
            f"💵 *Inversión:* {cantidad_usdt:.2f} USDT"
        )
        self.notifier.enviar_mensaje(msg)

    def cerrar_posicion(self, asset, precio_mercado, label="UNKNOWN", motivo="CLOSED_SIGNAL"):
        """Cierra una posición de inmediato y procesa beneficios/pérdidas."""
        if asset not in self.posiciones:
            return
            
        data = self.posiciones[asset]
        side = data.get('side', 'LONG')
        
        # 1. CÁLCULO FINANCIERO
        if side == "LONG":
            variacion = (precio_mercado / data['entrada']) - 1
        else:
            variacion = (data['entrada'] / precio_mercado) - 1
            
        beneficio_neto = data['cantidad'] * variacion
        
        self.balance_actual += beneficio_neto
        self.margen_en_uso -= data['cantidad']
        self.guardar_balance_persistente()
        
        # 2. ACTUALIZAR BASE DE DATOS
        try:
            session = Session()
            op_db = session.query(Operacion).filter_by(asset=asset, status="OPEN").first()
            if op_db:
                op_db.status = motivo
                op_db.fecha_cierre = datetime.utcnow()
                op_db.resultado_neto = beneficio_neto
                session.commit()
            session.close()
        except Exception as e:
            print(f"⚠️ Error al actualizar BD en cierre por señal: {e}")
            
        # 3. NOTIFICACIÓN TELEGRAM
        msg_cierre = (
            f"🐋 *CIERRE DE POSICIÓN*\n\n"
            f"👤 *Perfil:* {label}\n"
            f"📦 *Activo:* {asset}\n"
            f"📊 *Motivo:* {motivo}\n"
            f"💰 *Precio Cierre:* {precio_mercado:.4f}\n"
            f"💸 *Resultado:* {beneficio_neto:.2f} USDT\n"
            f"🏦 *Balance Total:* {self.balance_actual:.2f} USDT"
        )
        self.notifier.enviar_mensaje(msg_cierre)
        
        # 4. FEEDBACK EN CONSOLA
        print(f"\n🐋 [{motivo}] Activo {asset}")
        print(f"   Resultado: {beneficio_neto:.2f} USDT")
        print(f"   Balance Guardado: {self.balance_actual:.2f} USDT")
        
        del self.posiciones[asset]

    def gestionar_salidas(self, precios_actuales):
        """
        Vigila las posiciones abiertas y las cierra si tocan SL o TP.
        """
        for asset, data in list(self.posiciones.items()):
            precio_hoy = precios_actuales.get(asset)
            if not precio_hoy:
                continue

            side = data.get('side', 'LONG')
            if side == "LONG":
                toca_sl = precio_hoy <= data['sl']
                toca_tp = precio_hoy >= data['tp']
            else:
                toca_sl = precio_hoy >= data['sl']
                toca_tp = precio_hoy <= data['tp']

            if toca_sl or toca_tp:
                resultado_str = "CIERRE TP" if toca_tp else "CIERRE SL"
                
                # 1. CÁLCULO FINANCIERO
                if side == "LONG":
                    variacion = (precio_hoy / data['entrada']) - 1
                else:
                    variacion = (data['entrada'] / precio_hoy) - 1
                    
                beneficio_neto = data['cantidad'] * variacion
                
                # Actualizamos el balance y liberamos el margen retenido
                self.balance_actual += beneficio_neto
                self.margen_en_uso -= data['cantidad']
                
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
                msg_cierre = (
                    f"{emoji} *POSICIÓN CERRADA*\n\n"
                    f"📦 *Activo:* {asset}\n"
                    f"📊 *Motivo:* {resultado_str}\n"
                    f"💰 *Precio Cierre:* {precio_hoy:.4f}\n"
                    f"💸 *Resultado:* {beneficio_neto:.2f} USDT\n"
                    f"🏦 *Balance Total:* {self.balance_actual:.2f} USDT"
                )
                self.notifier.enviar_mensaje(msg_cierre)

                # 4. FEEDBACK EN CONSOLA
                print(f"\n💰 [{resultado_str}] en {asset}")
                print(f"   Resultado: {beneficio_neto:.2f} USDT")
                print(f"   Balance Guardado: {self.balance_actual:.2f} USDT")
                
                del self.posiciones[asset]