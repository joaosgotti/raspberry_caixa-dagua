# config.py
import os
import sys
from dotenv import load_dotenv

# Carrega variáveis do .env para o ambiente
dotenv_file_path = os.path.join(os.path.dirname(__file__), '.env')

if not load_dotenv(dotenv_path=dotenv_file_path, override=True):
    print(f"[Config] ERRO CRÍTICO: Arquivo de configuração '{dotenv_file_path}' não encontrado ou não pôde ser lido.")
    print("[Config] Verifique se o arquivo existe no local correto e tem permissões de leitura.")
    print("[Config] O programa não pode continuar sem as configurações.")
    sys.exit(1)
else:
    print(f"[Config] Arquivo '{dotenv_file_path}' carregado com sucesso (com override).")

# --- Configurações MQTT ---
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT_STR = os.getenv("MQTT_PORT")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC")
MQTT_KEEPALIVE_STR = os.getenv("MQTT_KEEPALIVE")

# --- Configurações Sensor RPi ---
GPIO_TRIG_PIN_STR = os.getenv("GPIO_TRIG_PIN")
GPIO_ECHO_PIN_STR = os.getenv("GPIO_ECHO_PIN")
PUBLISH_INTERVAL_SECONDS_STR = os.getenv("PUBLISH_INTERVAL_SECONDS")
MIN_NIVEL = os.getenv("MIN_NIVEL")
MAX_NIVEL = os.getenv("MAX_NIVEL")

# --- Configurações Banco de Dados ---
DB_HOST = os.getenv("DB_HOST")
DB_PORT_STR = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# --- Validação e Conversão Mínima ---
def get_int_env(var_str, var_name, default=None):
    """
    Valida e converte uma variável de ambiente para inteiro.
    """
    if var_str is None:
        if default is not None:
            print(f"[Config] Aviso: {var_name} não definida, usando padrão {default}.")
            return default
        else:
            print(f"[Config] ERRO: Variável obrigatória {var_name} não definida no .env!")
            sys.exit(1)
    try:
        return int(var_str)
    except ValueError:
        print(f"[Config] ERRO: {var_name} ('{var_str}') não é um número inteiro!")
        sys.exit(1)

# MQTT
MQTT_PORT = get_int_env(MQTT_PORT_STR, "MQTT_PORT")
MQTT_KEEPALIVE = get_int_env(MQTT_KEEPALIVE_STR, "MQTT_KEEPALIVE", default=60)

if not all([MQTT_BROKER, MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC]):
     print("[Config] ERRO: Configurações MQTT obrigatórias ausentes no .env!")
     sys.exit(1)

# Sensor
GPIO_TRIG_PIN = get_int_env(GPIO_TRIG_PIN_STR, "GPIO_TRIG_PIN")
GPIO_ECHO_PIN = get_int_env(GPIO_ECHO_PIN_STR, "GPIO_ECHO_PIN")
PUBLISH_INTERVAL_SECONDS = get_int_env(PUBLISH_INTERVAL_SECONDS_STR, "PUBLISH_INTERVAL_SECONDS", default=60)

# Banco de Dados
DB_PORT = get_int_env(DB_PORT_STR, "DB_PORT")

print("[Config] Configurações processadas.")
print(f"[Config] MQTT -> Broker: {MQTT_BROKER}:{MQTT_PORT}, Tópico: {MQTT_TOPIC}")
print(f"[Config] Sensor -> Intervalo: {PUBLISH_INTERVAL_SECONDS}s, GPIO: {GPIO_TRIG_PIN}/{GPIO_ECHO_PIN}")

def check_db_config_present():
    """Verifica se todas as variáveis de configuração do banco de dados estão presentes."""
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("[Config] ERRO: Configurações de Banco de Dados obrigatórias ausentes no .env!")
        return False
    print(f"[Config] DB -> Host: {DB_HOST}:{DB_PORT}, DB: {DB_NAME}")
    return True