# main.py

import sensor_reader
import os
import time
from datetime import datetime
from database_handler import DatabaseHandler
from dotenv import load_dotenv
from collections import deque
import statistics

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
MOVING_AVERAGE_WINDOW = float(os.getenv("MOVING_AVERAGE_WINDOW"))

recent_readings = deque(maxlen=MOVING_AVERAGE_WINDOW)

def run_publisher_with_sensor():
    """
    Função principal para executar o ciclo de leitura da MEDIANA do sensor,
    aplicar média móvel e publicar/inserir no banco de dados.
    """

    print("Inicializando GPIO via sensor_reader...")
    if not sensor_reader.setup_gpio():
        print("ERRO CRÍTICO: Falha ao inicializar GPIO. Encerrando.")
        return

    try:
        while True:
            median_distance_value = sensor_reader.get_median_distance()
            if median_distance_value is not None:
                recent_readings.append(median_distance_value)

                if len(recent_readings) == MOVING_AVERAGE_WINDOW:
                    moving_average = round(statistics.mean(recent_readings))

                    if moving_average > MIN_NIVEL*(1-TOLERANCIA) or moving_average > MAX_NIVEL*(1+TOLERANCIA):
                        created_on = datetime.now()
                        print(f"Média Móvel: {moving_average} cm | created_on: {created_on}")
                        DatabaseHandler().insert_reading(moving_average, created_on)
                    else:
                        print("[Publisher Main] Média móvel fora do intervalo esperado. Pulando a inserção.")
                else:
                    print(f"[Publisher Main] Aguardando mais leituras para média móvel ({len(recent_readings)}/{MOVING_AVERAGE_WINDOW})")
            else:
                print("[Publisher Main] Falha ao obter a mediana do sensor. Pulando.")

            time.sleep(PUBLISH_INTERVAL_SECONDS)

    except Exception:
        print("ERRO CRÍTICO: Falha inesperada no loop principal do publicador.")
        import traceback
        traceback.print_exc()

run_publisher_with_sensor()