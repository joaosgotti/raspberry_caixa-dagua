import time
import datetime
import os
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json

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

# Função para medir a distância
def medir_distancia():
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()

    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distancia = pulse_duration * 17150
    return round(distancia, 2)


# Função para publicar no mqtt
def publicar(distancia):
    payload = {
        "distancia": distancia,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    client.publish("sensor/distancia", json.dumps(payload))

# Função principal para iniciar as medições continuamente
def iniciar_medicoes():
    while True:
	try:
        	distancia = medir_distancia()
        	print(f"Distância medida: {distancia} cm")
		publicar(distancia)
	except Exeption as e:
		print(f"Erro ao medir ou publicar: {e}")
	
	time.sleep(10)

if __name__ == "__main__":
    try:
        iniciar_medicoes()
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        GPIO.cleanup()
print(f"Erro ao medir ou publicar: {e}")print(f"Erro ao medir ou publicar: {e}")
