# main.py

import sensor_reader
import os
import time
from datetime import datetime
from database_handler import DatabaseHandler
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()



GPIO_TRIG_PIN = int(os.getenv("GPIO_TRIG_PIN"))
GPIO_ECHO_PIN = int(os.getenv("GPIO_ECHO_PIN"))
PUBLISH_INTERVAL_SECONDS = int(os.getenv("PUBLISH_INTERVAL_SECONDS"))

MIN_NIVEL = float(os.getenv("MIN_NIVEL"))
MAX_NIVEL = float(os.getenv("MAX_NIVEL"))

NUM_READINGS_PER_CYCLE = int(os.getenv("NUM_READINGS_PER_CYCLE"))
READING_INTERVAL_SECONDS = float(os.getenv("READING_INTERVAL_SECONDS"))
STABILIZATION_TIME = float(os.getenv("STABILIZATION_TIME"))

SPEED_OF_SOUND_CM_S = float(os.getenv("SPEED_OF_SOUND_CM_S"))
TRIGGER_PULSE_DURATION_S = float(os.getenv("TRIGGER_PULSE_DURATION_S"))
SETTLE_TIME_S = float(os.getenv("SETTLE_TIME_S"))
MAX_ECHO_WAIT_S = float(os.getenv("MAX_ECHO_WAIT_S"))
MAX_VALID_PULSE_S = float(os.getenv("MAX_VALID_PULSE_S"))
MIN_VALID_PULSE_S = float(os.getenv("MIN_VALID_PULSE_S"))
TOLERANCIA = float(os.getenv("TOLERANCIA")) 

def run_publisher_with_sensor():
    """
    Função principal para executar o ciclo de leitura da MEDIANA do sensor e publicação via MQTT.
    """

    print("Inicializando GPIO via sensor_reader...")
    if not sensor_reader.setup_gpio():
        print("ERRO CRÍTICO: Falha ao inicializar GPIO. Encerrando.")
        return

    try:
        while True:
            # Lê a MEDIANA da distância
            median_distance_value = sensor_reader.get_median_distance()
            if median_distance_value is not None:
                # Validação básica da MEDIANA lida
                if MIN_NIVEL*(1-TOLERANCIA) < median_distance_value <= MAX_NIVEL*(1+TOLERANCIA):
                    print(f"Mediana do sensor: {median_distance_value} cm (Válida)")

                    created_on = datetime.now().isoformat() # Usa o timezone UTC e formato ISO
                    DatabaseHandler().insert_reading(median_distance_value, created_on)
                else:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Fora da faixa esperada, ignorando)")
            else:
                print("[Publisher Main] Falha ao obter a mediana do sensor. Pulando a publicação.")

            sleep_time = PUBLISH_INTERVAL_SECONDS
            time.sleep(sleep_time) 

    except Exception:
        print("ERRO CRÍTICO: Falha inesperada no loop principal do publicador.")
        import traceback
        traceback.print_exc()

run_publisher_with_sensor()
