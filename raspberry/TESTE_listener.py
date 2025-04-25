#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# simple_listener.py
# Script procedural ultra-simples para ESCUTAR mensagens MQTT.

import paho.mqtt.client as mqtt
import ssl
import time
import sys
import os

# --- Configurações Hardcoded ---
MQTT_BROKER = "0d88ad4901824e80a0a920db5c7d2aca.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "joaosgotti"         # <<< SEU USUARIO REAL
MQTT_PASSWORD = "sS123412"     # <<< SUA SENHA REAL
MQTT_TOPIC = "sensor/default_topic" # <<< TÓPICO PARA ESCUTAR
CLIENT_ID = f"simple_listener_pi_{os.getpid()}"

print("--- Iniciando Listener Simples ---")
print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Tópico: {MQTT_TOPIC}")
print(f"ID Cliente: {CLIENT_ID}")

# --- Callbacks Essenciais ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Chamado ao conectar (ou falhar)."""
    if rc == 0:
        print("[Listener] Conectado ao Broker com sucesso!")
        print(f"[Listener] Inscrevendo no tópico '{MQTT_TOPIC}'...")
        # Inscreve após conectar
        subscribe_result, mid = client.subscribe(MQTT_TOPIC, qos=1)
        if subscribe_result != mqtt.MQTT_ERR_SUCCESS:
            print(f"[Listener] ERRO ao tentar inscrever: {mqtt.error_string(subscribe_result)}")
    else:
        print(f"[Listener] Falha na conexão, código: {rc} - {mqtt.connack_string(rc)}")

def on_disconnect(client, userdata, rc, properties=None):
    """Chamado ao desconectar."""
    print(f"[Listener] Desconectado. Código: {rc} - {mqtt.error_string(rc)}")
    if rc != 0:
        print("[Listener] Desconexão inesperada...")

def on_message(client, userdata, msg):
    """Chamado quando uma mensagem chega."""
    try:
        payload_str = msg.payload.decode('utf-8')
        print(f"\n>>> MENSAGEM RECEBIDA <<<")
        print(f"  Tópico: {msg.topic}")
        print(f"  Payload: {payload_str}")
    except Exception as e:
        print(f"\n>>> Erro ao processar mensagem: {e}")
        print(f"  Payload Raw: {msg.payload}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """Chamado para confirmar inscrição (opcional)."""
    print(f"[Listener] Inscrito com sucesso (MID: {mid}) QoS: {granted_qos}")

# --- Criação e Configuração do Cliente ---
print("Criando cliente...")
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_subscribe = on_subscribe # Opcional, mas útil

print("Configurando usuário/senha e TLS...")
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_PORT == 8883:
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

# --- Conexão e Loop Principal ---
try:
    print("Conectando...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

    print("Iniciando loop principal (loop_forever)... Ctrl+C para sair.")
    client.loop_forever() # Mantém a conexão, recebe mensagens, reconecta

except KeyboardInterrupt:
    print("\nSaindo por solicitação do usuário...")
except Exception as e:
    print(f"\nErro inesperado no loop: {e}")
finally:
    print("Limpando...")
    client.disconnect()
    print("Listener finalizado.")