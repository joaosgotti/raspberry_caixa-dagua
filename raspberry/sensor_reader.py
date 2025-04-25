# sensor_reader.py
import RPi.GPIO as GPIO
import time
import config # Usa os pinos definidos no config

# Configuração GPIO (feita uma vez na importação)
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(config.GPIO_TRIG_PIN, GPIO.OUT)
    GPIO.setup(config.GPIO_ECHO_PIN, GPIO.IN)
    GPIO.output(config.GPIO_TRIG_PIN, GPIO.LOW)
    print(f"[Sensor] GPIO inicializado (TRIG={config.GPIO_TRIG_PIN}, ECHO={config.GPIO_ECHO_PIN})")
    time.sleep(0.5) # Pausa para estabilizar
except Exception as e:
    print(f"[Sensor] ERRO CRÍTICO ao inicializar GPIO: {e}")
    print("Verifique as permissões (use sudo?) e a conexão do sensor.")
    # Não podemos continuar sem GPIO
    import sys
    sys.exit(1)

def read_distance():
    """
    Mede a distância usando o sensor HC-SR04.

    Retorna:
        float | None: Distância em centímetros (arredondada para uma casa decimal)
                      ou None em caso de erro ou timeout.
    """
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
                print("[Sensor] Timeout ao esperar ECHO HIGH.")
                return None

        pulse_end_time = time.time()
        timeout_limit = pulse_end_time + 0.1 # Outro timeout para segurança

        # Espera o pino ECHO ir para LOW (fim do pulso)
        while GPIO.input(config.GPIO_ECHO_PIN) == GPIO.HIGH:
            pulse_end_time = time.time()
            if pulse_end_time > timeout_limit:
                print("[Sensor] Timeout ao esperar ECHO LOW.")
                return None

        pulse_duration = pulse_end_time - pulse_start_time
        distance = (pulse_duration * 34300) / 2 # Velocidade do som em cm/s
        return round(distance, 1)

    except RuntimeError as e:
        print(f"[Sensor] Erro de Runtime GPIO na leitura: {e}")
        cleanup_gpio()
        raise # Re-levanta o erro para o chamador lidar (main_publisher)
    except Exception as e:
        print(f"[Sensor] Erro inesperado na leitura: {e}")
        return None # Retorna None para indicar falha na leitura

def cleanup_gpio():
    """Libera os recursos GPIO utilizados por este módulo."""
    print("[Sensor] Limpando GPIO...")
    try:
        GPIO.cleanup((config.GPIO_TRIG_PIN, config.GPIO_ECHO_PIN)) # Limpa apenas os pinos usados
        print("[Sensor] GPIO limpo.")
    except Exception as e:
        print(f"[Sensor] Erro ao limpar GPIO: {e}")