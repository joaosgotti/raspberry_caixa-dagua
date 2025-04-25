# sensor_reader_median.py
import RPi.GPIO as GPIO
import time
import statistics # Para calcular a mediana
import config     # Usa os pinos definidos no config
import sys        # Para sys.exit em caso de erro crítico

# --- Constantes ---
NUM_READINGS_PER_CYCLE = 7       # Quantas leituras fazer por ciclo
MIN_VALID_READINGS = 5       # Mínimo de leituras válidas para calcular a mediana (ex: > 50%)
READING_INTERVAL_SECONDS = 1 # Intervalo (em segundos) entre as leituras dentro de um ciclo
PUBLISH_INTERVAL_SECONDS = 60    # Intervalo (em segundos) entre os ciclos de cálculo da mediana

# --- Configuração GPIO ---
# (Movida para uma função para clareza e para poder chamar novamente se necessário)
def setup_gpio():
    """Inicializa os pinos GPIO para o sensor."""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(config.GPIO_TRIG_PIN, GPIO.OUT)
        GPIO.setup(config.GPIO_ECHO_PIN, GPIO.IN)
        # Garante que o pino TRIG comece em LOW
        GPIO.output(config.GPIO_TRIG_PIN, GPIO.LOW)
        print(f"[Sensor] GPIO inicializado (TRIG={config.GPIO_TRIG_PIN}, ECHO={config.GPIO_ECHO_PIN})")
        time.sleep(0.5) # Pausa para estabilizar o sensor
        return True
    except Exception as e:
        print(f"[Sensor] ERRO CRÍTICO ao inicializar GPIO: {e}")
        print("Verifique as permissões (use sudo?) e a conexão do sensor.")
        return False

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
        # Usa um loop com timeout para evitar travamento
        while GPIO.input(config.GPIO_ECHO_PIN) == GPIO.LOW:
            pulse_start_time = time.time()
            if pulse_start_time > timeout_limit:
                # print("[Sensor] Timeout ao esperar ECHO HIGH.") # Logar pode ser muito verboso aqui
                return None

        pulse_end_time = time.time()
        timeout_limit = pulse_end_time + 0.2 # Aumenta um pouco o timeout para o fim do pulso

        # Espera o pino ECHO ir para LOW (fim do pulso)
        while GPIO.input(config.GPIO_ECHO_PIN) == GPIO.HIGH:
            pulse_end_time = time.time()
            if pulse_end_time > timeout_limit:
                # print("[Sensor] Timeout ao esperar ECHO LOW.") # Logar pode ser muito verboso aqui
                return None

        pulse_duration = pulse_end_time - pulse_start_time

        # Verifica duração razoável (evita valores absurdos se algo der errado)
        # Max range ~4m -> ~23ms pulse. Min range ~2cm -> ~0.1ms pulse
        if pulse_duration < 0.0001 or pulse_duration > 0.025:
             # print(f"[Sensor] Duração do pulso fora do esperado: {pulse_duration:.5f}s")
             return None

        distance = (pulse_duration * 34300) / 2 # Velocidade do som em cm/s
        return round(distance, 1)

    except RuntimeError as e:
        # Este erro geralmente indica um problema mais sério com o GPIO
        print(f"[Sensor] Erro de Runtime GPIO na leitura: {e}")
        # Em um sistema maior, talvez sinalizar para reiniciar o setup do GPIO
        # Por ora, apenas retornamos None para indicar falha nesta leitura
        return None
    except Exception as e:
        print(f"[Sensor] Erro inesperado na leitura: {e}")
        return None # Retorna None para indicar falha na leitura

def get_median_distance(num_readings=NUM_READINGS_PER_CYCLE,
                        min_valid=MIN_VALID_READINGS,
                        interval=READING_INTERVAL_SECONDS):
    """
    Realiza múltiplas leituras de distância e retorna a mediana.

    Args:
        num_readings (int): Número de leituras a serem feitas.
        min_valid (int): Número mínimo de leituras válidas necessárias para calcular a mediana.
        interval (float): Tempo em segundos a esperar entre as leituras.

    Returns:
        float | None: A mediana das leituras válidas em cm, ou None se não houver
                      leituras válidas suficientes ou ocorrer um erro crítico.
    """
    readings = []
    print(f"[Sensor] Coletando {num_readings} leituras...")
    for i in range(num_readings):
        distance = read_distance()
        if distance is not None:
            # Opcional: Adicionar validação de faixa (ex: ignorar leituras < 2cm ou > 400cm)
            # if 2 < distance < 400:
            #    readings.append(distance)
            # else:
            #    print(f"[Sensor] Leitura {i+1}/{num_readings} descartada (fora da faixa): {distance} cm")
            readings.append(distance)
            print(f"[Sensor] Leitura {i+1}/{num_readings}: {distance:.1f} cm")
        else:
            print(f"[Sensor] Leitura {i+1}/{num_readings}: Falhou")

        # Espera um pouco entre as leituras para o sensor estabilizar
        if i < num_readings - 1: # Não espera após a última leitura
             time.sleep(interval)

    if len(readings) >= min_valid:
        median_distance = statistics.median(readings)
        print(f"[Sensor] Leituras válidas: {len(readings)}/{num_readings}. Mediana calculada.")
        return round(median_distance, 1)
    else:
        print(f"[Sensor] Não foi possível calcular a mediana ({len(readings)}/{num_readings} leituras válidas, mínimo necessário: {min_valid}).")
        return None

def cleanup_gpio():
    """Libera os recursos GPIO utilizados."""
    print("[Sensor] Limpando GPIO...")
    try:
        # Limpa apenas os pinos que configuramos
        GPIO.cleanup((config.GPIO_TRIG_PIN, config.GPIO_ECHO_PIN))
        print("[Sensor] GPIO limpo.")
    except Exception as e:
        print(f"[Sensor] Erro ao limpar GPIO: {e}")

# --- Loop Principal ---
if __name__ == "__main__":
    if not setup_gpio():
        sys.exit(1) # Sai se o GPIO não puder ser inicializado

    try:
        while True:
            start_time = time.time()
            print(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} --- Iniciando ciclo de medição ---")

            median_value = get_median_distance()

            if median_value is not None:
                print(f"=============================================")
                print(f" MEDIANA DA DISTÂNCIA: {median_value:.1f} cm")
                print(f"=============================================")
                # Aqui seria o ponto para "publicar" o valor (ex: MQTT, API, etc.)
                # Exemplo: publish_to_mqtt(topic="sensor/distance/median", value=median_value)
            else:
                print("---------------------------------------------")
                print(" Não foi possível obter a mediana neste ciclo.")
                print("---------------------------------------------")

            # Calcula quanto tempo esperar para completar o ciclo de PUBLISH_INTERVAL_SECONDS
            end_time = time.time()
            elapsed_time = end_time - start_time
            sleep_time = max(0, PUBLISH_INTERVAL_SECONDS - elapsed_time)

            print(f"Ciclo levou {elapsed_time:.2f}s. Aguardando {sleep_time:.2f}s para o próximo ciclo.")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[Main] Interrupção recebida (Ctrl+C). Encerrando...")
    except Exception as e:
        print(f"\n[Main] Erro inesperado no loop principal: {e}")
    finally:
        cleanup_gpio()
        print("[Main] Programa finalizado.")