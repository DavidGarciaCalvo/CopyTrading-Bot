import requests
from config import Config

class SignalProvider:
    def __init__(self):
        self.api_key = Config.HELIUS_API_KEY
        self.wallets_dict = Config.WALLETS_TO_TRACK
        self.last_signatures = {wallet: None for wallet in self.wallets_dict.keys()}
        
    def get_signal(self, mock=False):
        if mock:
            return [{
                "asset": "SOL/USDT", 
                "side": "LONG", 
                "signature": "MOCK_SIG_INICIAL", 
                "label": "TEST_SISTEMA"
            }]

        nuevas_señales = []
        stables = ["USDC", "USDT", "USDH", "UXD"]

        for wallet, label in self.wallets_dict.items():
            url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={self.api_key}"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    transactions = response.json()
                    
                    if not isinstance(transactions, list) or len(transactions) == 0:
                        continue

                    latest_sig = transactions[0].get("signature")
                    
                    if not latest_sig or latest_sig == self.last_signatures[wallet]:
                        continue

                    # Sincronización inicial para no operar lo pasado
                    if self.last_signatures[wallet] is None:
                        self.last_signatures[wallet] = latest_sig
                        print(f"📡 Sincronizado: [{label}] {wallet[:5]}...")
                        continue
                    
                    # Recopilar TODAS las transacciones nuevas hasta la última conocida
                    txs_nuevas = []
                    for tx in transactions:
                        if tx.get("signature") == self.last_signatures[wallet]:
                            break
                        txs_nuevas.append(tx)

                    # Actualizamos el puntero a la más reciente
                    self.last_signatures[wallet] = latest_sig

                    # Procesamos en orden cronológico (de la más antigua a la más nueva)
                    for tx in reversed(txs_nuevas):
                        sig = tx.get("signature")
                        target_token = None

                        # --- ESTRATEGIA DE DETECCIÓN UNIFICADA ---
                        
                        # 1. Intentamos por eventos de SWAP (Lógica de pares SOL/USDC)
                        if tx.get("type") == "SWAP":
                            events = tx.get("events") or {}
                            swap_data = events.get("swap") or {}
                            
                            native_out = swap_data.get("nativeOutput") or {}
                            native_in = swap_data.get("nativeInput") or {}
                            
                            token_recibido = native_out.get("symbol", "")
                            token_entregado = native_in.get("symbol", "")

                            if token_recibido == "SOL" or (token_recibido in stables and token_entregado == "SOL"):
                                target_token = "SOL"
                            else:
                                target_token = token_recibido

                        # 2. Si no es SWAP o no detectó token, usamos Transferencias (Todoterreno)
                        if not target_token:
                            token_transfers = tx.get("tokenTransfers") or []
                            for tfer in token_transfers:
                                if tfer.get("toUserAccount") == wallet:
                                    target_token = tfer.get("symbol")
                                    break

                        # 3. Validación Final y envío
                        if target_token and target_token not in stables:
                            señal = {
                                "asset": f"{target_token}/USDT", 
                                "side": "LONG",
                                "signature": sig,
                                "label": label
                            }
                            nuevas_señales.append(señal)
                            print(f"🎯 ¡Movimiento detectado! [{label}] Activo: {target_token}")
                else:
                    # Si es error de servidor (502, 500), no mostramos el HTML sucio
                    msg = response.text[:100]
                    if response.status_code >= 500:
                        msg = "Fallo temporal del servidor Helius (Reintentando...)"
                    print(f"⚠️ Error API Helius [{response.status_code}] en {wallet[:5]}...: {msg}")

            except Exception as e:
                print(f"❌ Error de conexión/proceso en {wallet[:5]}...: {e}")
        
        return nuevas_señales