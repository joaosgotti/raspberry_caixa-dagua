import time
import datetime
import os
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import statistics
import ssl  

# Configuração do GPIO (sem mudanças)
GPIO.setwarnings(False)
TRIG = 23
ECHO = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Use as credenciais que você anotou do HiveMQ Cloud
MQTT_BROKER = "0d88ad4901824e80a0a920db5c7d2aca.s1.eu.hivemq.cloud"  # <<< SUBSTITUA PELO SEU HOST HIVEMQ
MQTT_PORT = 8883                     # <<< PORTA TLS DO HIVEMQ
MQTT_USER = "joaosgotti"   # <<< SUBSTITUA PELO SEU USUÁRIO HIVEMQ
MQTT_PASSWORD = "sS123412" # <<< SUBSTITUA PELA SUA SENHA HIVEMQ
MQTT_TOPIC = "sensor/distancia"      # Tópico para publicar (pode manter ou mudar)
# --- Fim das Configurações MQTT ---

# --- Cliente MQTT ---
# Adicionado callbacks para diagnóstico
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MQTT] Conectado ao Broker com sucesso!")
    else:
        print(f"[MQTT] Falha na conexão, código de retorno={rc}")
        print("[MQTT] Verifique host, porta, usuário, senha e configuração TLS.")

def on_disconnect(client, userdata, rc, properties=None):
    print(f"[MQTT] Desconectado do broker (código: {rc}).")

def on_publish(client, userdata, mid):
    # Este callback confirma que a mensagem foi enviada do cliente
    # Não garante que o broker recebeu/processou totalmente
    # print(f"[MQTT] Mensagem (mid={mid}) publicada.")
    pass # Geralmente não precisamos logar cada publish

# Cria o cliente
client_id = f"raspberrypi_sensor_{os.getpid()}" # ID único
client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

# Define os callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

# --- Configura Autenticação e TLS - ADICIONADO ---
print(f"[MQTT] Configurando conexão para {MQTT_BROKER}:{MQTT_PORT}...")
try:
    # Define usuário e senha ANTES de conectar
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    print("[MQTT] Usuário/Senha definidos.")

    # Configura TLS (necessário para porta 8883 do HiveMQ Cloud)
    print("[MQTT] Configurando TLS...")
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
    print("[MQTT] TLS configurado.")
except Exception as e:
    print(f"[MQTT] Erro ao configurar autenticação ou TLS: {e}")
    # Você pode querer sair do script aqui se a configuração falhar
    # exit()
# --- Fim da Configuração de Autenticação e TLS ---

# --- Conexão e Loop MQTT ---
try:
    print("[MQTT] Conectando ao broker...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60) # Tenta conectar
except Exception as e:
    print(f"[MQTT] Erro fatal ao tentar conectar: {e}")
    print("[MQTT] Verifique as configurações e a conexão de rede. Encerrando.")
    GPIO.cleanup() # Limpa GPIO antes de sair
    exit() # Sai se não conseguir conectar inicialmente

client.loop_start() # Inicia o loop MQTT em background para lidar com conexão/publicação
print("[MQTT] Loop iniciado em background.")
# --- Fim da Conexão e Loop ---


# --- Constantes de Medição (sem mudanças) ---
NUM_LEITURAS_MEDIANA = 7
INTERVALO_ENTRE_LEITURAS_MS = 1000
INTERVALO_PUBLICACAO_S = 30
DISTANCIA_MIN_VALIDA_CM = 1
DISTANCIA_MAX_VALIDA_CM = 180

# --- Função medir_distancia (sem mudanças) ---
def medir_distancia():
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()
        if pulse_start - timeout_start > 0.1:
             # print("Timeout: Eco não iniciou.") # Removido log excessivo
             return None
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()
        if pulse_end - timeout_start > 0.1:
            # print("Timeout: Eco não terminou.") # Removido log excessivo
            return None
    pulse_duration = pulse_end - pulse_start
    distancia = (pulse_duration * 34300) / 2
    # Arredonda para inteiro, como no seu código original
    return round(distancia)


# --- Função publicar (sem mudanças) ---
def publicar(distancia_mediana):
    payload = {
        "distancia": distancia_mediana,
        "timestamp": datetime.datetime.now().isoformat()
    }
    try:
        # Publica com QoS 1 para maior garantia (requer mais recursos)
        # QoS 0 é "at most once", QoS 1 é "at least once", QoS 2 é "exactly once"
        result = client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        # Não precisamos esperar explicitamente com wait_for_publish com loop_start()
        # A biblioteca lida com isso em background.
        # result.wait_for_publish(timeout=5.0)
        print(f"  -> Tentativa de publicação (mid={result.mid}): {payload}")
        # A confirmação real viria no callback on_publish se necessário
    except Exception as e:
        print(f"  -> Erro ao tentar publicar no MQTT: {e}")


# --- Função iniciar_medicoes_com_mediana (sem mudanças) ---
def iniciar_medicoes_com_mediana():
    print("Iniciando medições...")
    while True:
        # Verifica se o cliente MQTT ainda está conectado antes de medir
        if not client.is_connected():
             print("[MQTT] Desconectado. Aguardando reconexão automática...")
             time.sleep(5) # Espera um pouco antes de checar novamente
             continue # Pula para a próxima iteração do loop

        leituras = []
        # print(f"\nColetando {NUM_LEITURAS_MEDIANA} leituras...") # Log menos verboso

        for i in range(NUM_LEITURAS_MEDIANA):
            dist = medir_distancia()
            if dist is not None and DISTANCIA_MIN_VALIDA_CM < dist < DISTANCIA_MAX_VALIDA_CM:
                # print(f"  Leitura {i+1}: {dist} cm (Válida)")
                leituras.append(dist)
            # Elif/Else para logs de leituras inválidas/timeouts foram removidos para diminuir a verbosidade
            elif dist is not None:
                 pass # Ignora inválida
            else:
                 pass # Ignora timeout

            time.sleep(INTERVALO_ENTRE_LEITURAS_MS / 1000.0)

        if len(leituras) >= 3:
            mediana = statistics.median(leituras)
            # print(f"Leituras válidas: {leituras}") # Log menos verboso
            print(f"Mediana calculada: {mediana:.1f} cm. Publicando...") # Arredonda para 1 decimal
            publicar(round(mediana, 1)) # Publica mediana com 1 decimal
        else:
            print(f"Leituras válidas insuficientes ({len(leituras)}). Pulando publicação.")

        # print(f"Aguardando {INTERVALO_PUBLICACAO_S} segundos...") # Log menos verboso
        time.sleep(INTERVALO_PUBLICACAO_S)

# --- Bloco Principal (sem mudanças na lógica) ---
if __name__ == "__main__":
    try:
        iniciar_medicoes_com_mediana()
    except KeyboardInterrupt:
        print("\nEncerrando...")
    except Exception as e:
         print(f"\nErro inesperado no loop principal: {e}")
    finally:
        print("Limpando GPIO...")
        GPIO.cleanup()
        if client.is_connected():
            print("Desconectando MQTT...")
            client.loop_stop() # Para o loop do MQTT
            client.disconnect()
        print("Programa finalizado.")