import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime
import json

# Função para se conectar ao banco de dados PostgreSQL
def connect_db():
    try:
        connection = psycopg2.connect(
            dbname="caixa_dagua",
            user="postgres",
            password="1234",  # Substitua pela sua senha
            host="localhost",
            port="5432"
        )
        return connection
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Função para inserir leitura na tabela
def inserir_leitura(cursor, distancia, timestamp):
    try:
        cursor.execute("""
            INSERT INTO leituras (distancia, timestamp)
            VALUES (%s, %s);
        """, (distancia, timestamp))
        cursor.connection.commit()
        print(f"Leitura inserida: {distancia}, {timestamp}")
    except psycopg2.Error as e:
        print(f"Erro ao inserir leitura: {e}")

# Função para processar a mensagem recebida
def processar_mensagem(payload):
    try:
        dados = json.loads(payload)  # Usar json para evitar problemas com eval
        distancia = dados['distancia']
        timestamp = datetime.strptime(dados['timestamp'], "%Y-%m-%d %H:%M:%S")
        return distancia, timestamp
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Erro ao processar a mensagem: {e}")
        return None, None

# Função callback para quando uma mensagem MQTT for recebida
def on_message(client, userdata, message):
    payload = message.payload.decode()  # Decodifica a mensagem
    print(f"Mensagem recebida: {payload}")
    
    distancia, timestamp = processar_mensagem(payload)
    
    if distancia is not None and timestamp is not None:
        # Conectar ao banco de dados e inserir a leitura
        connection = connect_db()
        if connection:
            cursor = connection.cursor()
            inserir_leitura(cursor, distancia, timestamp)
            cursor.close()
            connection.close()

# Configuração do cliente MQTT
def configurar_mqtt():
    client = mqtt.Client()
    client.on_message = on_message

    try:
        client.connect("192.168.0.49", 1884, 60)  # Conecte-se ao broker MQTT
        client.subscribe("sensor/distancia")  # Inscreva-se no tópico
        print("Conectado ao broker MQTT e pronto para receber mensagens.")
    except Exception as e:
        print(f"Erro ao conectar ao broker MQTT: {e}")
        return None
    return client

# Função principal para iniciar o cliente MQTT
def main():
    client = configurar_mqtt()
    if client:
        client.loop_forever()  # Loop para manter o cliente MQTT funcionando e recebendo mensagens

if __name__ == "__main__":
    main()

