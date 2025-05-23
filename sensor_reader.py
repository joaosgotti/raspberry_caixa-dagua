# sensor_reader.py

import RPi.GPIO as GPIO
import time
import statistics
import os        
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

def setup_gpio():
    """Inicializa os pinos GPIO para o sensor. Chamado uma vez pelo script principal."""
    try:
        # load_dotenv()
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(GPIO_TRIG_PIN, GPIO.OUT)
        GPIO.setup(GPIO_ECHO_PIN, GPIO.IN)
        GPIO.output(GPIO_TRIG_PIN, GPIO.LOW) # Garante que o pino TRIG comece em LOW
        time.sleep(STABILIZATION_TIME) # Pausa para estabilizar o sensor
        print("[Sensor Mod] GPIO configurado com sucesso.")
        return True
    except Exception as e:
        print(f"[Sensor Mod] ERRO CRÍTICO ao inicializar GPIO: {e} - Verifique as conexões.")
        return False

def cleanup_gpio():
    """Libera os recursos GPIO utilizados. Chamado uma vez pelo script principal no final."""
    try:
        GPIO.cleanup(GPIO_TRIG_PIN, GPIO_ECHO_PIN)
        print("[Sensor Mod] GPIO limpo.")
    except Exception as e:
        print(f"[Sensor Mod] Aviso: Erro ao limpar GPIO (pode já ter sido limpo ou setup falhou): {e}")

def read_distance():
    """
    Mede a distância usando o sensor HC-SR04.
    """
    # Adiciona um pequeno atraso antes de disparar para evitar ecos fantasmas da leitura anterior
    time.sleep(SETTLE_TIME_S)

    try:
        GPIO.output(GPIO_TRIG_PIN, GPIO.HIGH)
        time.sleep(TRIGGER_PULSE_DURATION_S)
        GPIO.output(GPIO_TRIG_PIN, GPIO.LOW)

        # Medição do tempo de eco
        pulse_start_time = time.time()
        timeout_limit = pulse_start_time + MAX_ECHO_WAIT_S

        # Espera o pino ECHO ir para HIGH (início do pulso)
        while GPIO.input(GPIO_ECHO_PIN) == GPIO.LOW:
            pulse_start_time = time.time()
            if pulse_start_time > timeout_limit:
                return None

        pulse_end_time = time.time()
        timeout_limit = pulse_end_time + 2*MAX_ECHO_WAIT_S

        # Espera o pino ECHO ir para LOW (fim do pulso)
        while GPIO.input(GPIO_ECHO_PIN) == GPIO.HIGH:
            pulse_end_time = time.time()
            if pulse_end_time > timeout_limit:
                return None

        pulse_duration = pulse_end_time - pulse_start_time

        # Verifica duração razoável (evita valores absurdos)
        if (pulse_duration < MIN_VALID_PULSE_S) or (pulse_duration > MAX_VALID_PULSE_S):
             return None

        distance = (pulse_duration * SPEED_OF_SOUND_CM_S)/ 2 
        return float(round(distance))

    except RuntimeError as e:
        print(f"[Sensor Mod] Erro de Runtime GPIO na leitura: {e}")
        return None
    except Exception as e:
        print(f"[Sensor Mod] Erro inesperado na leitura: {e}")
        return None

def get_median_distance():
    """
    Realiza múltiplas leituras de distância e retorna a mediana.
    """
    readings = []
    print(f"[Sensor Mod] Coletando leituras...")
    for i in range(NUM_READINGS_PER_CYCLE):
        distance = read_distance() 
        if distance is not None:
            readings.append(distance)

        if i < NUM_READINGS_PER_CYCLE - 1:
             time.sleep(READING_INTERVAL_SECONDS)

    if readings:
        median_distance = statistics.median(readings)
        print(f"[Sensor Mod] Mediana: {median_distance} cm.")
        return median_distance
    else:
        print(f"[Sensor Mod] Não foi possível calcular a mediana")
        return None

