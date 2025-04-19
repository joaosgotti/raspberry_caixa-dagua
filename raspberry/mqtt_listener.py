import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import os
import ssl

# --- Configurações de Banco de Dados ---
DB_NAME = "postgresql_caixa_dagua"
DB_USER = "postgresql_caixa_dagua_user"
DB_PASSWORD = "1PR9xJvT26exLhwry5Xyv0qThzKM01dz"
DB_HOST = "dpg-d01h3u3uibrs73aqbang-a.oregon-postgres.render.com"
DB_PORT = 5432

# --- Configurações do MQTT ---
MQTT_BROKER = "0d88ad4901824e80a0a920db5c7d2aca.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "joaosgotti"
MQTT_PASSWORD = "sS123412"

# --- Função de Conexão com o Banco de Dados ---
def connect_db():
    required_vars = {
        'DB_NAME': DB_NAME,
        'DB_USER': DB_USER,
        'DB_PASSWORD': DB_PASSWORD,
        'DB_HOST': DB_HOST
    }
    missing_vars = [k for k, v in required_vars.items() if not v]

    if missing_vars:
        print(f"Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None

    try:
        print(f"Tentando conectar ao DB: host={DB_HOST}, db={DB_NAME}, user={DB_USER}...")
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except psycopg2.OperationalError as e:
        print(f"Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        return None
    except psycopg2.Error as e:
        print(f"Erro psycopg2 ao conectar ao banco de dados: {e}")
        return None
    except Exception as e:
        print(f"Erro INESPERADO durante a conexão com o banco de dados: {e}")
        return None

# --- Funções Auxiliares ---
def inserir_leitura(cursor, distancia, timestamp):
    try:
        cursor.execute("""
            INSERT INTO leituras (distancia, timestamp)
            VALUES (%s, %s);
        """, (distancia, timestamp))
        cursor.connection.commit()
        print(f"Leitura inserida: Distancia={distancia} cm, Timestamp={timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    except psycopg2.Error as e:
        print(f"Erro ao inserir leitura: {e}")
        if cursor and cursor.connection:
            cursor.connection.rollback()

def processar_mensagem(payload_str):
    try:
        dados = json.loads(payload_str)
        distancia = dados['distancia']
        timestamp_str = dados['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str)

        if not isinstance(distancia, (int, float)):
            raise ValueError(f"Distancia recebida não é um número: {distancia}")

        return distancia, timestamp
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Erro ao processar a mensagem: {e}")
        print(f"Payload problemático: {payload_str}")
        return None, None
    except Exception as e:
        print(f"Erro inesperado ao processar mensagem: {e}")
        print(f"Payload problemático: {payload_str}")
        return None, None

# --- Callbacks MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Conectado ao Broker MQTT com sucesso (Código: {rc})")
        topic = os.getenv("MQTT_TOPIC", "sensor/distancia")
        try:
            client.subscribe(topic)
            print(f"Inscrito no tópico: {topic}")
        except Exception as e:
            print(f"Erro ao se inscrever no tópico {topic}: {e}")
    else:
        print(f"Falha na conexão com o Broker MQTT (Código: {rc})")

def on_message(client, userdata, message):
    try:
        payload_str = message.payload.decode('utf-8')
        print(f"Mensagem recebida no tópico {message.topic}: {payload_str}")
    except UnicodeDecodeError as e:
        print(f"Erro ao decodificar payload: {e}")
        return

    distancia, timestamp = processar_mensagem(payload_str)

    if distancia is not None and timestamp is not None:
        connection = connect_db()
        if connection:
            cursor = None
            try:
                cursor = connection.cursor()
                inserir_leitura(cursor, distancia, timestamp)
            except Exception as e_db:
                print(f"Erro durante operação com banco de dados: {e_db}")
            finally:
                if cursor: cursor.close()
                if connection: connection.close()
    else:
        print("Falha ao processar a mensagem, dados não inseridos.")

def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        print(f"Desconexão inesperada do MQTT (Código: {rc}).")
    else:
        print("Desconectado do MQTT normalmente.")

# --- Configuração MQTT ---
def configurar_mqtt():
    mqtt_broker = os.getenv("MQTT_BROKER", MQTT_BROKER)
    mqtt_port = int(os.getenv("MQTT_PORT", MQTT_PORT))
    mqtt_user = os.getenv("MQTT_USER", MQTT_USER)
    mqtt_password = os.getenv("MQTT_PASSWORD", MQTT_PASSWORD)

    required_vars = {
        'MQTT_BROKER': mqtt_broker,
        'MQTT_USER': mqtt_user,
        'MQTT_PASSWORD': mqtt_password
    }
    missing_vars = [k for k, v in required_vars.items() if not v]

    if missing_vars:
        print(f"Erro Crítico: Variáveis de ambiente do MQTT ausentes: {', '.join(missing_vars)}")
        return None

    client_id = f"mqtt_listener_{os.getpid()}"
    try:
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    except Exception as e:
        print(f"Erro ao criar cliente MQTT: {e}")
        return None

    client.username_pw_set(mqtt_user, mqtt_password)

    if mqtt_port == 8883:
        try:
            print(f"Configurando TLS para conexão MQTT na porta {mqtt_port}...")
            client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
            print("TLS configurado.")
        except Exception as e:
            print(f"Erro ao configurar TLS: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        print(f"Tentando conectar ao Broker MQTT: {mqtt_broker}:{mqtt_port}...")
        client.connect(mqtt_broker, mqtt_port, 60)
        return client
    except Exception as e:
        print(f"Erro ao conectar ao broker MQTT: {e}")
        return None

# --- Função Principal ---
def main():
    print("Iniciando MQTT Listener...")
    client = configurar_mqtt()

    if client:
        print("Iniciando loop MQTT...")
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            print("\nInterrupção recebida. Encerrando...")
        except Exception as e:
            print(f"Erro no loop principal do MQTT: {e}")
        finally:
            if client:
                client.disconnect()
                print("Cliente MQTT desconectado.")
    else:
        print("Falha ao configurar ou conectar ao cliente MQTT. Encerrando.")

# --- Ponto de Entrada ---
if __name__ == "__main__":
    main()
