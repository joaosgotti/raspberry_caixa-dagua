# sensor_reader.py
import RPi.GPIO as GPIO
import time
import statistics # Para calcular a mediana
import config     # Usa os pinos definidos no config
import sys        # Usado raramente aqui, mas pode ser útil para logs

# --- Constantes ---
# Mantemos as constantes relacionadas à leitura aqui
NUM_READINGS_PER_CYCLE = 7       # Quantas leituras fazer por ciclo
MIN_VALID_READINGS = 4       # Mínimo de leituras válidas para calcular a mediana (ex: > 50%)
READING_INTERVAL_SECONDS = 0.1 # Intervalo (em segundos) entre as leituras DENTRO de um ciclo de mediana

# --- Funções de Configuração e Limpeza (Serão chamadas pelo main_publisher.py) ---
def setup_gpio():
    """Inicializa os pinos GPIO para o sensor. Chamado uma vez pelo script principal."""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.GPIO_TRIG_PIN, GPIO.OUT)
        GPIO.setup(config.GPIO_ECHO_PIN, GPIO.IN)
        # Garante que o pino TRIG comece em LOW
        GPIO.output(config.GPIO_TRIG_PIN, GPIO.LOW)
        print(f"[Sensor Mod] GPIO inicializado (TRIG={config.GPIO_TRIG_PIN}, ECHO={config.GPIO_ECHO_PIN})")
        time.sleep(0.5) # Pausa para estabilizar o sensor
        return True # Indica sucesso
    except Exception as e:
        print(f"[Sensor Mod] ERRO CRÍTICO ao inicializar GPIO: {e}")
        print("[Sensor Mod] Verifique as permissões (use sudo?) e a conexão do sensor.")
        return False # Indica falha

def cleanup_gpio():
    """Libera os recursos GPIO utilizados. Chamado uma vez pelo script principal no final."""
    print("[Sensor Mod] Limpando GPIO...")
    try:
        # Limpa apenas os pinos que configuramos
        GPIO.cleanup((config.GPIO_TRIG_PIN, config.GPIO_ECHO_PIN))
        print("[Sensor Mod] GPIO limpo.")
    except Exception as e:
        # Se o cleanup falhar, pode ser que o setup nunca tenha ocorrido, logar o erro.
        print(f"[Sensor Mod] Aviso: Erro ao limpar GPIO (pode já ter sido limpo ou setup falhou): {e}")

# --- Funções do Sensor ---
def read_distance():
    """
    Mede a distância usando o sensor HC-SR04.

    Retorna:
        float | None: Distância em centímetros (arredondada para uma casa decimal)
                      ou None em caso de erro ou timeout.
    """
    # Adiciona um pequeno atraso antes de disparar para evitar ecos fantasmas da leitura anterior
    time.sleep(0.02)

    try:
        # Pulso de disparo (trigger)
        GPIO.output(config.GPIO_TRIG_PIN, GPIO.HIGH)
        time.sleep(0.00001) # 10 microssegundos
        GPIO.output(config.GPIO_TRIG_PIN, GPIO.LOW)

        # Medição do tempo de eco
        pulse_start_time = time.time()
        timeout_limit = pulse_start_time + 0.1 # Timeout de 100ms

        # Espera o pino ECHO ir para HIGH (início do pulso)
        while GPIO.input(config.GPIO_ECHO_PIN) == GPIO.LOW:
            pulse_start_time = time.time()
            if pulse_start_time > timeout_limit:
                # print("[Sensor Mod] Timeout ao esperar ECHO HIGH.") # Log verboso opcional
                return None

        pulse_end_time = time.time()
        timeout_limit = pulse_end_time + 0.2 # Aumenta um pouco o timeout para o fim do pulso

        # Espera o pino ECHO ir para LOW (fim do pulso)
        while GPIO.input(config.GPIO_ECHO_PIN) == GPIO.HIGH:
            pulse_end_time = time.time()
            if pulse_end_time > timeout_limit:
                # print("[Sensor Mod] Timeout ao esperar ECHO LOW.") # Log verboso opcional
                return None

        pulse_duration = pulse_end_time - pulse_start_time

        # Verifica duração razoável (evita valores absurdos)
        if pulse_duration < 0.0001 or pulse_duration > 0.025:
             # print(f"[Sensor Mod] Duração do pulso fora do esperado: {pulse_duration:.5f}s")
             return None

        distance = (pulse_duration * 34300) / 2 # Velocidade do som em cm/s
        return round(distance, 1)

    except RuntimeError as e:
        # !! IMPORTANTE !! NÃO chamar cleanup_gpio() aqui!
        # Apenas reporta o erro e retorna None. O main_publisher decidirá o que fazer.
        print(f"[Sensor Mod] Erro de Runtime GPIO na leitura: {e}")
        # Este erro pode indicar que o setmode foi perdido, mas não podemos limpá-lo aqui.
        return None
    except Exception as e:
        print(f"[Sensor Mod] Erro inesperado na leitura: {e}")
        return None # Retorna None para indicar falha na leitura

def get_median_distance(num_readings=NUM_READINGS_PER_CYCLE,
                        min_valid=MIN_VALID_READINGS,
                        interval=READING_INTERVAL_SECONDS):
    """
    Realiza múltiplas leituras de distância e retorna a mediana.
    Chamado pelo script principal dentro do loop.

    Args:
        num_readings (int): Número de leituras a serem feitas.
        min_valid (int): Número mínimo de leituras válidas necessárias.
        interval (float): Tempo em segundos a esperar entre as leituras.

    Returns:
        float | None: A mediana das leituras válidas em cm, ou None se falhar.
    """
    readings = []
    print(f"[Sensor Mod] Coletando {num_readings} leituras...")
    for i in range(num_readings):
        distance = read_distance() # Chama a função de leitura individual
        if distance is not None:
            readings.append(distance)
            # print(f"[Sensor Mod] Leitura {i+1}/{num_readings}: {distance:.1f} cm") # Log verboso opcional
        # else:
            # print(f"[Sensor Mod] Leitura {i+1}/{num_readings}: Falhou") # Log verboso opcional

        # Espera um pouco entre as leituras para o sensor estabilizar
        if i < num_readings - 1:
             time.sleep(interval)

    if len(readings) >= min_valid:
        median_distance = statistics.median(readings)
        print(f"[Sensor Mod] Leituras válidas: {len(readings)}/{num_readings}. Mediana: {median_distance:.1f} cm.")
        return round(median_distance, 1)
    else:
        print(f"[Sensor Mod] Não foi possível calcular a mediana ({len(readings)}/{num_readings} leituras válidas, mínimo: {min_valid}).")
        return None

# Nota: NÃO HÁ MAIS o bloco if __name__ == "__main__": aqui.