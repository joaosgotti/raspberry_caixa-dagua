# config.py
import os
from dotenv import load_dotenv
import sys

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# --- Configurações MQTT ---
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensor/default_topic")

# --- Configurações Sensor RPi ---
GPIO_TRIG_PIN = int(os.getenv("GPIO_TRIG_PIN", 23))
GPIO_ECHO_PIN = int(os.getenv("GPIO_ECHO_PIN", 24))
DISTANCIA_MIN_VALIDA_CM = int(os.getenv("DISTANCIA_MIN_VALIDA_CM", 10))
DISTANCIA_MAX_VALIDA_CM = int(os.getenv("DISTANCIA_MAX_VALIDA_CM", 80))
NUM_LEITURAS_MEDIANA = int(os.getenv("NUM_LEITURAS_MEDIANA", 7))
INTERVALO_ENTRE_LEITURAS_MS = int(os.getenv("INTERVALO_ENTRE_LEITURAS_MS", 1000))
INTERVALO_PUBLICACAO_S = int(os.getenv("INTERVALO_PUBLICACAO_S", 60))
CLIENT_ID_PREFIX = os.getenv("CLIENT_ID_PREFIX", "rpi_sensor_") # Usado pelo publisher

# --- Configurações do Banco de Dados (para o Listener) ---
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))

# --- Validações ---
missing_mqtt = [k for k, v in {'MQTT_BROKER': MQTT_BROKER, 'MQTT_USER': MQTT_USER, 'MQTT_PASSWORD': MQTT_PASSWORD}.items() if not v]
if missing_mqtt:
    print(f"Erro Crítico: Variáveis de ambiente MQTT ausentes: {', '.join(missing_mqtt)}")
    print("Verifique seu arquivo .env")
    sys.exit(1) # Encerra se faltar config MQTT

missing_db = [k for k, v in {'DB_NAME': DB_NAME, 'DB_USER': DB_USER, 'DB_PASSWORD': DB_PASSWORD, 'DB_HOST': DB_HOST}.items() if not v]

print("[Config] Configurações carregadas do .env.")
print(f"[Config] MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}, Tópico: {MQTT_TOPIC}")


def check_db_config():
    """Verifica se as configurações de DB estão presentes."""
    if missing_db:
        print(f"Erro Crítico: Variáveis de ambiente do Banco de Dados ausentes no .env: {', '.join(missing_db)}")
        return False
    print(f"[Config] DB Config OK: Host={DB_HOST}:{DB_PORT}, DB={DB_NAME}")
    return True

def check_gpio_config():
    """Verifica se as configurações de GPIO estão presentes."""
    print(f"[Config] GPIO Config OK: TRIG={GPIO_TRIG_PIN}, ECHO={GPIO_ECHO_PIN}")
    return True