# cloud/back/mqtt_service.py
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print("Conectado ao broker MQTT com código de retorno", rc)
    client.subscribe("sensor/distancia")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] Mensagem recebida no tópico {msg.topic}: {payload}")
    try:
        dados = json.loads(payload)
        # Aqui você pode salvar no banco, em uma variável global, fila etc.
        print("Dados processados:", dados)
    except Exception as e:
        print("Erro ao processar payload:", e)

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("localhost", 1883, 60)
    client.loop_start()  # Não bloqueia, roda em paralelo
