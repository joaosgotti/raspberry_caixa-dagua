#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ultra_simple_listener.py
# Script procedural EXTREMAMENTE simples, com tudo hardcoded,
# para testar a conexão MQTT básica.

import paho.mqtt.client as mqtt
import ssl
import time
import sys
import traceback # Para_TOPIC}")
print(f"  Usuário: {MQTT_USER}")
print(f"  Client ID: {CLIENT_ID}")

# --- 2. Definir Funções de Callback ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback para quando a conexão é estabelecida (ou falha)."""
    connect_result_str = mqtt.connack_string(rc)
    print(f"--> [Callback on_connect] Resultado da Conexão: {rc} - {connect_result_str}")
    if rc == 0:
        print(f"--> [Callback on_connect] Conectado! Inscrevendo no tópico '{MQTT_TOPIC}'...")
        subscribe_result, mid = client.subscribe(MQTT_TOPIC, qos=1)
        if subscribe_result == mqtt.MQTT_ERR_SUCCESS:
            print(f"--> [Callback on_connect] Inscrição enviada (MID: {mid}). Aguardando SUBACK.")
        else:
            print(f"--> [Callback on_connect] ERRO ao tentar inscrever: {mqtt.error_string(subscribe_result)}")
    # Não precisa fazer mais nada aqui, loop_forever lida com reconexão

def on_disconnect(client, userdata, rc, properties=None):
    """Callback para quando a conexão é perdida."""
    disconnect_reason = mqtt.error_string(rc)
    print(f"--> [Callback on_disconnect] Desconectado! Código: {rc} - {disconnect_reason}")
    # O loop_forever tentará reconectar automaticamente se rc != 0 (e não for erro fatal)
    if rc != 0:
        print("--> [Callback on_disconnect] Tentativa de reconexão automática em breve...")

def on_message(client, userdata, msg):
    """Callback para quando uma mensagem é recebida."""
    try:
        payload_str = msg.payload.decode('utf-8')
        print(f"\n>>> [Callback on_message] Mensagem Recebida! Tópico='{msg.topic}', QoS={msg.qos}")
        print(f"    Payload='{payload_str}'")
        # Aqui você poderia adicionar lógica para processar o JSON, se quisesse,
        # mas para o teste mínimo, apenas imprimir é suficiente.
    except Exception as e:
        print(f">>> [Callback on_message] Erro ao processar mensagem: {e}")
        print(f"    Payload Raw (bytes): {msg.payload}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """Callback para confirmação de inscrição."""
    print(f"--> [Callback on_subscribe] Inscrição confirmada (MID: {mid}) QoS Concedido: {granted_qos}")

def on_log(client, userdata, level, buf):
    """Callback para logs internos do Paho (para debug)."""
    # Imprime logs de nível NOTICE, WARNING e ERROR para reduzir verbosidade,
    # mas ainda ver informações importantes e erros.
    # Comente o if e descomente o print abaixo para ver TUDO.
    if level >= mqtt.MQTT_LOG_NOTICE:
         print(f"    [PAHO LOG Lvl:{level}] {buf}")
    # print(f"    [PAHO LOG Lvl:{level}] {buf}") # Descomente para log DEBUG completo


# --- 3. Criar e Configurar Cliente MQTT ---
print("Criando cliente MQTT...")
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

# Atribuir callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_log = on_log # Ativa o log detalhado

# Configurar autenticação e TLS
print("Configurando autenticação e TLS...")
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_PORT == 8883:
    print("Habilitando TLS v1.2...")
    try:
        client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
    except Exception as e:
        print(f"ERRO CRÍTICO ao configurar TLS: {e}")
        sys.exit(1)
else:
    print("TLS não habilitado (porta diferente de 8883).")

# --- 4. Conectar e Iniciar Loop ---
try:
    print(f"Tentando conectar ao broker {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=KEEPALIVE_SECONDS)

    print("Conexão iniciada. Iniciando loop principal (loop_forever)...")
    print("------ Pressione Ctrl+C para sair ------")
    client.loop_forever() # Bloqueia aqui, roda o loop de rede e callbacks

except KeyboardInterrupt:
    print("\n------ Interrupção pelo usuário (Ctrl+C) ------")
except ssl.SSLError as e:
    print(f"\nERRO SSL durante conexão/loop: {e}")
    print("Verifique a configuração TLS, certificados CA do sistema, ou compatibilidade.")
except OSError as e:
     print(f"\nERRO DE REDE/OS durante conexão/loop: {e}")
     print("Verifique conectividade, DNS, firewall.")
except Exception as e:
    print(f"\nERRO INES imprimir tracebacks completos em erros")

print("--- Iniciando Teste MQTT Ultra Simples (Hardcoded) ---")

# --- 1. Configuração Hardcoded ---
MQTT_BROKER = "0d88ad4901824e80a0a920db5c7d2aca.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "joaosgotti"         # <<< COLOQUE SEU USUARIO REAL AQUI
MQTT_PASSWORD = "sS123412"     # <<< COLOQUE SUA SENHA REAL AQUI
MQTT_TOPIC = "sensor/default_topic" # <<< CONFIRME SE ESTE É O TÓPICO CORRETO
CLIENT_ID = f"ultra_simple_pi_{time.time():.0f}" # ID único simples
KEEPALIVE = 60 # Segundos

print("Usando a seguinte configuração:")
print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"  Tópico: {MQTT_TOPIC}")
print(f"  Usuário: {MQTT_USER}")
print(f"  Client ID: {CLIENT_ID}")
print(f"  Keepalive: {KEEPALIVE}s")

# --- 2. Definir Funções de Callback Essenciais ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback para conexão."""
    connect_result_str = mqtt.connack_string(rc)
    print(f"[Callback on_connect] Resultado: {rc} - {connect_result_str}")
    if rc == 0:
        print(f"  >> Conectado! Tentando inscrever em '{MQTT_TOPIC}'...")
        # Inscreve após conectar
        subscribe_result, mid = client.subscribe(MQTT_TOPIC, qos=1)
        if subscribe_result == mqtt.MQTT_ERR_SUCCESS:
            print(f"  >> Inscrição enviada (MID: {mid}).")
        else:
            print(f"  >> ERRO ao tentar inscrever: {mqtt.error_string(subscribe_result)}")
    else:
        print("  >> Falha na conexão inicial.") # Reconexão é tratada pelo loop

def on_disconnect(client, userdata, rc, properties=None):
    """Callback para desconexão."""
    disconnect_reason = mqtt.error_string(rc)
    print(f"[Callback on_disconnect] Desconectado! Código: {rc} - {disconnect_reason}")
    if rc != 0:
        print("  >> Desconexão inesperada.")
        # Não precisa explicitamente tentar reconectar aqui, loop_forever faz isso

def on_message(client, userdata, msg):
    """Callback para mensagem recebida."""
    try:
        payload = msg.payload.decode('utf-8')
        print(f"[Callback on_message] Mensagem: Tópico='{msg.topic}', Payload='{payload}'")
    except Exception as e:
        print(f"[Callback on_message] Erro processando msg: {e}, Payload Raw: {msg.payload}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """Callback para confirmação de inscrição."""
    print(f"[Callback on_subscribe] Inscrito! MID: {mid}, QoS: {granted_qos}")

def on_log(client, userdata, level, buf):
    """Callback para logs internos do Paho."""
    # Comente se ficar muito verboso, mas útil para PINGs e erros SSL
    print(f"[PAHO LOG Lvl:{level}] {buf}")

# --- 3. Criar, Configurar e Conectar Cliente MQTT ---
print("\nCriando cliente Paho MQTT...")
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

# Atribuir callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_log = on_log # Deixar log ativo para diagnóstico

# Configurar autenticação e TLS
print("Configurando Auth/TLS...")
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_PORT == 8883:
    print("TLS Habilitado.")
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

# --- 4. Conectar e Entrar no Loop ---
try:
    print(f"\nConectando a {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=KEEPALIVE)

    print("\nIniciando loop principal (loop_forever)... Pressione Ctrl+C para sair.")
    client.loop_forever() # Bloqueia, processa rede/callbacks, reconecta

except KeyboardInterrupt:
    print("\nSaindo por solicitação do usuário (Ctrl+C).")
except ssl.SSLError as e:
    print(f"\nERRO SSL irrecuperável: {e}")
    traceback.print_exc()
except OSError as e:
     print(f"\nERRO DE REDE/OS irrecuperável: {e}")
     traceback.print_exc()
except Exception as e:
    print(f"\nERRO INESPERADO irrecuperável: {e}")
    traceback.print_exc()
finally:
    # Limpeza
    print("Desconectando cliente MQTT...")
    client.disconnect()
    # client.loop_stop() # Não necessário com loop_forever se saindo por exceção/interrupt
    print("Cliente desconectado.")

print("\n--- Fim do Teste MQTT Ultra Simples ---")