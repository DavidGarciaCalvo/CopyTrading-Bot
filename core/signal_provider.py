import time
import requests
from config import Config


class SignalProvider:
    def __init__(self):
        self.api_key = Config.HELIUS_API_KEY
        self.wallets_dict = Config.WALLETS_TO_TRACK  # {wallet: label}
        self.last_signatures = {wallet: None for wallet in self.wallets_dict.keys()}

        # Anti-spam: máximo 1 señal cada X segundos por wallet
        self.last_trade_time = {wallet: 0 for wallet in self.wallets_dict.keys()}
        self.cooldown_seconds = 60

    def get_signal(self):
        nuevas_señales = []
        stables = ["USDC", "USDT", "USDH", "UXD"]

        for wallet, label in self.wallets_dict.items():
            url = (
                f"https://api.helius.xyz/v0/addresses/{wallet}/transactions"
                f"?api-key={self.api_key}&limit=100"
            )

            try:
                response = requests.get(url, timeout=10)

                if response.status_code != 200:
                    msg = response.text[:120]
                    if response.status_code >= 500:
                        msg = "Fallo temporal del servidor Helius (Reintentando...)"
                    print(f"⚠️ Error API Helius [{response.status_code}] en {wallet[:5]}...: {msg}")
                    continue

                transactions = response.json()
                if not isinstance(transactions, list) or len(transactions) == 0:
                    continue

                print(f"\n🔍 Wallet {label} ({wallet[:5]}...): Helius devolvió {len(transactions)} txs")

                latest_sig = (transactions[0] or {}).get("signature")
                if not latest_sig:
                    print("  ⚠️ Sin signature en la tx más reciente (raro).")
                    continue

                # Si ya estamos sincronizados y no hay cambios, saltamos
                if latest_sig == self.last_signatures[wallet]:
                    continue

                # Sincronización inicial: NO operamos el pasado
                if self.last_signatures[wallet] is None:
                    self.last_signatures[wallet] = latest_sig
                    print(f"  📡 Sincronizado: [{label}] {wallet[:5]}...")
                    continue

                # Recopilar TODAS las transacciones nuevas hasta la última conocida
                txs_nuevas = []
                for tx in transactions:
                    if (tx or {}).get("signature") == self.last_signatures[wallet]:
                        break
                    txs_nuevas.append(tx)

                print(f"  🧾 Txs nuevas encontradas: {len(txs_nuevas)}")

                # Actualizamos puntero a la más reciente (aunque luego descartemos señales)
                self.last_signatures[wallet] = latest_sig

                # Procesamos cronológico: antigua -> nueva
                for tx in reversed(txs_nuevas):
                    sig = (tx or {}).get("signature", "")
                    tx_type = (tx or {}).get("type")
                    token_transfers = (tx or {}).get("tokenTransfers") or []
                    native_transfers = (tx or {}).get("nativeTransfers") or []

                    print(
                        f"  ↳ TX {sig[:6]}... type={tx_type} | "
                        f"tokenTransfers={len(token_transfers)} | nativeTransfers={len(native_transfers)}"
                    )

                    # Modo seguro: ignorar todo lo que no sea SWAP
                    if tx_type != "SWAP":
                        continue

                    target_token = None
                    side = "LONG"

                                        # -------------------------------
                    # 1) INTENTO POR SWAP (modo robusto)
                    #    Preferimos inferir el token comprado por tokenTransfers:
                    #    - Sale stable de la wallet
                    #    - Entra token no-stable a la wallet
                    # -------------------------------
                    compro_con_stable = any(
                        (t.get("fromUserAccount") == wallet) and (t.get("symbol") in stables)
                        for t in token_transfers
                    )

                    token_entrante_no_stable = None
                    for t in token_transfers:
                        if (t.get("toUserAccount") == wallet) and (t.get("symbol") not in stables):
                            token_entrante_no_stable = t.get("symbol")
                            break

                    vendio_por_stable = any(
                        (t.get("toUserAccount") == wallet) and (t.get("symbol") in stables)
                        for t in token_transfers
                    )
                    token_saliente_no_stable = None
                    for t in token_transfers:
                        if (t.get("fromUserAccount") == wallet) and (t.get("symbol") not in stables):
                            token_saliente_no_stable = t.get("symbol")
                            break

                    if compro_con_stable and token_entrante_no_stable:
                        target_token = token_entrante_no_stable
                    elif vendio_por_stable and token_saliente_no_stable:
                        target_token = token_saliente_no_stable
                        side = "SELL"
                    else:
                        # Fallback a tu lógica anterior (por si Helius no rellena bien tokenTransfers)
                        events = (tx or {}).get("events") or {}
                        swap_data = events.get("swap") or {}

                        native_out = swap_data.get("nativeOutput") or {}
                        native_in = swap_data.get("nativeInput") or {}

                        token_recibido = native_out.get("symbol", "")  # lo que recibe
                        token_entregado = native_in.get("symbol", "")  # lo que entrega

                        # Tu lógica original “SOL vs stables”
                        if token_recibido == "SOL" or (token_recibido in stables and token_entregado == "SOL"):
                            target_token = "SOL"
                        else:
                            target_token = token_recibido or None

                    # -------------------------------
                    # 2A) TRANSFERENCIAS NATIVAS (SOL)
                    # (por seguridad, mantenemos esta detección como fallback)
                    # -------------------------------
                    if not target_token:
                        for nt in native_transfers:
                            if nt.get("toUserAccount") == wallet:
                                target_token = "SOL"
                                break

                    # -------------------------------
                    # 2B) TRANSFERENCIAS SPL (tokens)
                    # (fallback)
                    # -------------------------------
                    if not target_token:
                        for tfer in token_transfers:
                            if tfer.get("toUserAccount") == wallet:
                                target_token = tfer.get("symbol")
                                break

                    # -------------------------------
                    # 3) FILTRO DE “COMPRA/VENTA REAL”
                    # -------------------------------
                    if target_token and target_token not in stables:
                        if side == "LONG":
                            salio_stable = any((t.get("fromUserAccount") == wallet and t.get("symbol") in stables) for t in token_transfers)
                            if target_token != "SOL" and not salio_stable:
                                print(f"    ⚠️ Ignorada: entra {target_token} pero no sale stable (posible ruta/ruido/airdrop)")
                                continue
                        elif side == "SELL":
                            entro_stable = any((t.get("toUserAccount") == wallet and t.get("symbol") in stables) for t in token_transfers)
                            if target_token != "SOL" and not entro_stable:
                                print(f"    ⚠️ Ignorada: sale {target_token} pero no entra stable")
                                continue

                        # Cooldown por wallet (anti-spam)
                        now = time.time()
                        if now - self.last_trade_time[wallet] < self.cooldown_seconds:
                            print(f"    ⏳ Cooldown activo ({self.cooldown_seconds}s). Señal ignorada.")
                            continue
                        self.last_trade_time[wallet] = now

                        señal = {
                            "asset": f"{target_token}/USDT",
                            "side": side,
                            "signature": sig,
                            "label": label
                        }
                        nuevas_señales.append(señal)
                        accion_str = "COMPRA" if side == "LONG" else "VENTA"
                        print(f"    ✅ ¡Movimiento detectado! [{label}] {accion_str} Activo: {target_token}")

            except Exception as e:
                print(f"❌ Error de conexión/proceso en {wallet[:5]}...: {e}")

        return nuevas_señales