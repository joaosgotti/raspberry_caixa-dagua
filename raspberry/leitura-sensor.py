import time
import datetime
import os
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import statistics  # Importa a biblioteca de estatísticas

# Configuração do GPIO
GPIO.setwarnings(False)
TRIG = 23
ECHO = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Definir Broker MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/distancia"

# Cliente MQTT
client = mqtt.Client(client_id="raspberrypi_sensor") # Adicionar um client_id é boa prática
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start() # Inicia o loop do MQTT em background

# --- Constantes ---
NUM_LEITURAS_MEDIANA = 7 # Número de leituras para calcular a mediana
INTERVALO_ENTRE_LEITURAS_MS = 1000 # Intervalo em milissegundos entre as leituras para a mediana
INTERVALO_PUBLICACAO_S = 30 # Intervalo em segundos entre cada publicação da mediana
DISTANCIA_MIN_VALIDA_CM = 1   # Mínimo razoável para o HC-SR04
DISTANCIA_MAX_VALIDA_CM = 180 # Máximo razoável para o HC-SR04

# Função para medir a distância (sem mudanças, mas adiciona retorno None para timeout)
def medir_distancia():
    # Garante que o TRIG esteja baixo inicialmente
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.05) # Pequena pausa

    # Envia o pulso ultrassônico
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001) # Pulso de 10 microssegundos
    GPIO.output(TRIG, GPIO.LOW)

    # Mede o tempo de espera pelo início do pulso de eco
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()
        if pulse_start - timeout_start > 0.1: # Timeout de 100ms se não receber eco
             print("Timeout: Eco não iniciou.")
             return None

    # Mede o tempo de duração do pulso de eco
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()
        if pulse_end - timeout_start > 0.1: # Timeout de 100ms se o eco não terminar
            print("Timeout: Eco não terminou.")
            return None

    pulse_duration = pulse_end - pulse_start
    # Fórmula: Distancia (cm) = (Tempo * VelocidadeDoSom) / 2
    # Velocidade do som ~ 34300 cm/s
    distancia = (pulse_duration * 34300) / 2
    return round(distancia, 2)

# Função para publicar no mqtt (sem mudanças na lógica principal)
def publicar(distancia_mediana):
    payload = {
        # Usaremos 'distancia' como chave para manter consistência com o frontend
        "distancia": distancia_mediana,
        "timestamp": datetime.datetime.now().isoformat() # Usar formato ISO 8601 é mais padrão
    }
    try:
        result = client.publish(MQTT_TOPIC, json.dumps(payload))
        result.wait_for_publish(timeout=5.0) # Espera um pouco pela confirmação
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
             print(f"  -> Publicado: {payload}")
        else:
             print(f"  -> Falha ao publicar MQTT: {mqtt.error_string(result.rc)}")
    except Exception as e:
        print(f"  -> Erro ao publicar no MQTT: {e}")


# Função principal modificada
def iniciar_medicoes_com_mediana():
    print("Iniciando medições (calculando mediana de 5 leituras)...")
    while True:
        leituras = []
        print(f"\nColetando {NUM_LEITURAS_MEDIANA} leituras...")

        for i in range(NUM_LEITURAS_MEDIANA):
            dist = medir_distancia()
            if dist is not None and DISTANCIA_MIN_VALIDA_CM < dist < DISTANCIA_MAX_VALIDA_CM:
                print(f"  Leitura {i+1}: {dist} cm (Válida)")
                leituras.append(dist)
            elif dist is not None:
                 print(f"  Leitura {i+1}: {dist} cm (Inválida - Fora do range {DISTANCIA_MIN_VALIDA_CM}-{DISTANCIA_MAX_VALIDA_CM} cm)")
            else:
                 print(f"  Leitura {i+1}: Falha (Timeout)")

            # Pequena pausa entre as leituras para evitar ecos sobrepostos
            time.sleep(INTERVALO_ENTRE_LEITURAS_MS / 1000.0)

        # Verifica se temos leituras suficientes para calcular a mediana
        if len(leituras) >= 3: # Exige pelo menos 3 leituras válidas
            mediana = statistics.median(leituras)
            print(f"Leituras válidas: {leituras}")
            print(f"Mediana calculada: {mediana:.2f} cm")
            publicar(round(mediana, 2)) # Publica a mediana arredondada
        else:
            print(f"Não há leituras válidas suficientes ({len(leituras)}) para calcular a mediana. Pulando publicação.")

        # Espera antes do próximo ciclo de medição
        print(f"Aguardando {INTERVALO_PUBLICACAO_S} segundos para o próximo ciclo...")
        time.sleep(INTERVALO_PUBLICACAO_S)

if __name__ == "__main__":
    try:
        iniciar_medicoes_com_mediana() # Chama a nova função
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        print("Limpando GPIO...")
        GPIO.cleanup()
        print("Desconectando MQTT...")
        client.loop_stop() # Para o loop do MQTT
        client.disconnect()
        print("Programa finalizado.")