# mqtt_listener.py
import paho.mqtt.client as mqtt
import ssl
import config # Importa as configurações
import json
from datetime import datetime
from database_handler import DatabaseHandler # Importa nossa classe de DB

class MQTTListener:
    """Classe simples para escutar MQTT e chamar o DB Handler."""

    def __init__(self, db_handler: DatabaseHandler): # Recebe a instância do DB handler
        self.db_handler = db_handler # Armazena a instância
        self.client_id = f"simple_listener_pi_{os.getpid()}"
        print(f"[Listener] Criando cliente com ID: {self.client_id}")
        # clean_session=True (padrão) requer re-inscrição no on_connect
        self.client = mqtt.Client(client_id=self.4300) / 2

        return round(distance, 1) # Retorna com 1 casa decimal

    except RuntimeError as e:
        print(f"[Sensor] Erro de Runtime GPIO: {e}. Pode precisar reiniciar.")
        # Em caso de erro crítico, limpar pode ser problemático,
        # mas vamos tentar para liberar os pinos se possível.
        cleanup_gpio()
        return None
    except Exception as e:
        print(f"[Sensor] Erro inesperado na medição: {e}")
        return None

def cleanup_gpio():
    """Libera os recursos GPIO."""
    print("[Sensor] Limpando GPIO...")
    try:
        GPIO.cleanup()
        print("[Sensor] GPIO limpo.")
    except Exception as e:
        print(f"[Sensor] Erro ao limpar GPIO: {e}")