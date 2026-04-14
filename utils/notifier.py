import telebot
from config import Config

class TelegramNotifier:
    def __init__(self):
        self.enabled = False
        if Config.TELEGRAM_TOKEN and Config.TELEGRAM_CHAT_ID:
            try:
                self.bot = telebot.TeleBot(Config.TELEGRAM_TOKEN)
                self.chat_id = Config.TELEGRAM_CHAT_ID
                self.enabled = True
            except Exception as e:
                print(f"⚠️ Error inicializando Telegram: {e}")

    def enviar_mensaje(self, texto):
        if self.enabled:
            try:
                # Escapamos caracteres problemáticos comunes para evitar el Error 400
                texto_seguro = texto.replace("_", "\\_")
                
                # Enviamos usando Markdown clásico
                self.bot.send_message(self.chat_id, texto_seguro, parse_mode='Markdown')
            except Exception as e:
                # Si falla el Markdown, lo intentamos enviar como texto normal (sin negritas)
                # Así nos aseguramos de que el aviso llegue SÍ O SÍ
                try:
                    self.bot.send_message(self.chat_id, texto)
                except:
                    print(f"⚠️ Error crítico en Telegram: {e}")