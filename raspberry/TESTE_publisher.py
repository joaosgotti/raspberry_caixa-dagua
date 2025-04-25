#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# simple_publisher.py
# Script procedural ultra-simples para PUBLICAR dados (simulados).

import paho.mqtt.client as mqtt
import ssl
import time
import json
from datetime import datetime, timezone
import sys
import os

# --- Configurações Hardcoded ---
MQTT_BROKER = "0d88ad4901824e80a0a920db5c7d2aca.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "joaosgotti"         # <<< SEU USUARIO REAL
MQTT_PASSWORD = "sS123412"     # <<< SUA SENHA REAL
MQTT_TOPIC = "sensor/default_topic" # <<< TÓPICO PARA PUBLICAR
CLIENT_ID = f"simple_publisher_pi_{os.getpid()}"
PUBLISH_INTERVAL_SECONDS = 10 # Intervalo entre publicações

print("--- Iniciando Publisher Simples ---")
print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Tópico: {MQTT_TOPIC}")
print(f"ID Cliente: {CLIENT_ID}")

# --- Callbacks Essenciais (Mínimos) ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Chamado ao conectar (ou falhar)."""
    if rc == 0:
        print("[Publisher] Conectado ao Broker com sucesso!")
    else:
        print(f"[Publisher] Falha na conexão, código: {rc} - {mqtt.connack_string(rc)}")
        # O loop tentará reconectar se não for erro de autenticação grave

def on_disconnect(client, userdata, rc, properties=None):
    """Chamado ao desconectar."""
    print(f"[Publisher] Desconectado. Código: {rc} - {mqtt.error_string(rc)}")
    if rc != 0:
        print("[Publisher] Desconexão inesperada...")

def on_publish(client, userdata, mid):
    """Chamado após um publish QoS 1 ou 2 ser confirmado (opcional)."""
    # Descomente se quiser confirmação para cada mensagem
    # print(f"[Publisher] Mensagem (MID: {mid}) publicada.")
    pass

# --- Criação e Configuração do Cliente ---
print("Criando cliente...")
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish # Opcional

print("Configurando usuário/senha e TLS...")
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_PORT == 8883:
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

# --- Conexão e Loop de Publicação ---
try:
    print("Conectando...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    print("Iniciando loop de rede em background (loop_start)...")
    client.loop_start() # Necessário para processar callbacks e reconexões

    # Espera inicial para garantir a conexão antes de publicar
    time.sleep(5)

    message_counter = 0
    print("\n--- Iniciando publicação (Ctrl+C para parar) ---")
    while True:
        if client.is_connected():
            message_counter += 1
            # Cria payload simulado
            payload_dict = {
                "distancia": 10 + (message_counter % 10), # Valor de exemplo variado
                "created_on": datetime.now(timezone.utc).isoformat() # Timestamp ISO com UTC
            }
            payload_json = json.dumps(payload_dict)

            # Publica com QoS 1
            result, mid = client.publish(MQTT_TOPIC, payload_json, qos=1)

            if result == mqtt.MQTT_ERR_SUCCESS:
                print(f"Publicado (MID: {mid}): {payload_json}")
            else:
                 print(f"Erro ao tentar publicar (antes de enviar): {mqtt.error_string(result)}")

            # Espera para o próximo ciclo
            time.sleep(PUBLISH_INTERVAL_SECONDS)
        else:
            print("Desconectado. Aguardando reconexão automática...")
            time.sleep(5) # Espera antes de checar de novo

except KeyboardInterrupt:
    print("\nInterrupção detectada. Encerrando...")
except Exception as e:
    print(f"\nErro inesperado no loop principal: {e}")
finally:
    print("Limpando...")
    client.loop_stop() # Para o loop de background
    client.disconnect()
    print("Publisher finalizado.")