# sensor_hc_sr04.py
import RPi.GPIO as GPIO
import time
import config # Importa as configurações de pinos
from typing import Optional

class SensorDistancia:
    """Classe para interagir com o sensor ultrassônico HC-SR04."""

    def __init__(self, trig_pin=config.GPIO_TRIG_PIN, echo_pin=config.GPIO_ECHO_PIN):
        """Inicializa o sensor e configura os pinos GPIO."""
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.velocidade_som_cm_s = 34300 # Velocidade do som em cm/s

        print(f"[Sensor] Inicializando GPIO (BCM), TRIG={self.trig_pin}, ECHO={self.echo_pin}")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        # Garante que o pino TRIG comece em nível baixo
        GPIO.output(self.trig_pin, GPIO.LOW)
        time.sleep(0.5) # Pequena pausa após setup
        print("[Sensor] GPIO inicializado.")

    def medir(self) -> Optional[float]:
        """
        Realiza uma medição de distância.

        Returns:
            A distância medida em centímetros (float) ou None se ocorrer timeout/erro.
        """
        try:
            # Envia um pulso ultrassônico curto (10 microssegundos)
            GPIO.output(self.trig_pin, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(self.trig_pin, GPIO.LOW)

            # Mede o tempo de espera pelo início do pulso de eco
            timeout_start = time.time()
            pulse_start = None
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.1: # Timeout de 100ms
                    #print("[Sensor] Timeout esperando início do eco.")
                    return None

            # Mede a duração do pulso de eco
            timeout_start = time.time()
            pulse_end = None
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end - timeout_start > 0.1: # Timeout de 100ms
                    #print("[Sensor] Timeout esperando fim do eco.")
                    return None

            # Calcula a duração do pulso
            if pulse_start is None or pulse_end is None:
                 #print("[Sensor] Não foi possível capturar o pulso de eco completo.")
                 return None

            pulse_duration = pulse_end - pulse_start

            # Calcula a distância
            distancia_cm = (pulse_duration * self.velocidade_som_cm_s) / 2

            # Retorna como float para manter precisão antes de arredondar para publicar
            return float(distancia_cm)

        except RuntimeError as e:
             # Captura erros comuns do RPi.GPIO, como acesso concorrente ou setup inválido
             print(f"[Sensor] Erro de Runtime GPIO durante a medição: {e}")
             print("[Sensor] Pode ser necessário reiniciar o script ou verificar o hardware.")
             # Tentar limpar pode causar mais erros se o estado do GPIO estiver inconsistente
             # self.cleanup()
             return None
        except Exception as e:
            print(f"[Sensor] Erro inesperado durante a medição: {e}")
            return None

    def cleanup(self):
        """Libera os recursos GPIO."""
        print("[Sensor] Limpando GPIO...")
        GPIO.cleanup()
        print("[Sensor] GPIO limpo.")