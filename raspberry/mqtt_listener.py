import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import os
import ssl
from dotenv import load_dotenv # CORRIGIDO: from ... import ...

# Carrega variáveis do .env se existir (para teste local)
load_dotenv()

# --- Função de Conexão com o Banco de Dados ---
def connect_db():
    """
    Connects to the PostgreSQL database using credentials from environment variables.
    Returns a connection object or None if connection fails or variables are missing.
    """
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")

    required_vars = {
        'DB_NAME': db_name,
        'DB_USER': db_user,
        'DB_PASSWORD': db_password,
        'DB_HOST': db_host
    }
    missing_vars = [k for k, v in required_vars.items() if not v]

    if missing_vars:
        print(f"Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        print("  -> Certifique-se de que elas estão definidas no ambiente do Render ou no seu arquivo .env local.")
        return None

    try:
        print(f"Tentando conectar ao DB: host={db_host}, db={db_name}, user={db_user}...")
        connection = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except psycopg2.OperationalError as e:
        print(f"Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        print(f"  Verifique: Host ({db_host}), Porta ({db_port}), Regras de Acesso no Render, Status do DB.")
        return None
    except psycopg2.Error as e:
        print(f"Erro psycopg2 ao conectar ao banco de dados: {e}")
        print(f"  Verifique: Usuário ({db_user}), Senha (está correta?), Nome do DB ({db_name}).")
        return None
    except Exception as e:
         print(f"Erro INESPERADO durante a conexão com o banco de dados: {e}")
         return None

# --- Funções Auxiliares de Processamento e Inserção ---
def inserir_leitura(cursor, distancia, timestamp):
    """Insere uma leitura no banco de dados."""
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
            cursor.connection.rollback() # Desfaz a transação em caso de erro

def processar_mensagem(payload_str):
    """
    Processa o payload JSON string recebido via MQTT.
    Retorna (distancia, timestamp) ou (None, None).
    """
    try:
        dados = json.loads(payload_str)
        distancia = dados['distancia']
        timestamp_str = dados['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str) # Usa fromisoformat

        if not isinstance(distancia, (int, float)):
            raise ValueError(f"Distancia recebida não é um número: {distancia}")
        # datetime.fromisoformat já garante que é datetime se não der erro

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
    """Callback executado quando a conexão MQTT é estabelecida."""
    if rc == 0:
        print(f"Conectado ao Broker MQTT com sucesso (Código: {rc})")
        topic = os.getenv("MQTT_TOPIC", "sensor/distancia") # Tópico padrão ou do env
        try:
            client.subscribe(topic)
            print(f"Inscrito no tópico: {topic}")
        except Exception as e:
            print(f"Erro ao se inscrever no tópico {topic}: {e}")
    else:
        print(f"Falha na conexão com o Broker MQTT (Código: {rc}). Verifique credenciais, TLS, host/porta.")

def on_message(client, userdata, message):
    """Callback executado quando uma mensagem MQTT é recebida."""
    payload_str = ""
    try:
        payload_str = message.payload.decode('utf-8')
        print(f"Mensagem recebida no tópico {message.topic}: {payload_str}")
    except UnicodeDecodeError as e:
        print(f"Erro ao decodificar payload: {e}")
        print(f"Payload (bytes): {message.payload}")
        return # Aborta se não puder decodificar

    distancia, timestamp = processar_mensagem(payload_str)

    if distancia is not None and timestamp is not None:
        connection = connect_db() # Tenta conectar ao DB para esta mensagem
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
                # print("Conexão com o banco de dados fechada.") # Log opcional
    else:
        print("Falha ao processar a mensagem, dados não inseridos.")

def on_disconnect(client, userdata, rc, properties=None):
    """Callback executado quando o cliente MQTT desconecta."""
    if rc != 0:
        print(f"Desconexão inesperada do MQTT (Código: {rc}). O cliente pode tentar reconectar dependendo da configuração.")
    else:
        print("Desconectado do MQTT normalmente.")

# --- Função de Configuração e Conexão MQTT ---
def configurar_mqtt():
    """
    Configura e conecta o cliente MQTT usando variáveis de ambiente.
    Retorna o objeto client conectado ou None em caso de falha.
    """
    mqtt_broker = os.getenv("MQTT_BROKER")
    try:
        mqtt_port = int(os.getenv("MQTT_PORT", "8883"))
    except ValueError:
        print("Aviso: MQTT_PORT inválida no ambiente, usando porta padrão 8883.")
        mqtt_port = 8883
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")

    required_vars = {
        'MQTT_BROKER': mqtt_broker,
        'MQTT_USER': mqtt_user,
        'MQTT_PASSWORD': mqtt_password
    }
    missing_vars = [k for k, v in required_vars.items() if not v]

    if missing_vars:
        print(f"Erro Crítico: Variáveis de ambiente do MQTT ausentes: {', '.join(missing_vars)}")
        print("  -> Certifique-se de que elas estão definidas no ambiente do Render ou no seu arquivo .env local.")
        return None

    client_id = f"mqtt_listener_{os.getpid()}" # ID de cliente único
    try:
        # Tenta criar o cliente (pode falhar se paho-mqtt não estiver instalado)
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    except NameError:
         print("Erro: A classe mqtt.Client não foi encontrada. O Paho-MQTT está instalado?")
         return None
    except Exception as e:
        print(f"Erro ao criar cliente MQTT: {e}")
        return None


    client.username_pw_set(mqtt_user, mqtt_password) # Define usuário/senha

    # Configura TLS se a porta for 8883 (padrão HiveMQ Cloud)
    if mqtt_port == 8883:
        try:
            print(f"Configurando TLS para conexão MQTT na porta {mqtt_port}...")
            client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
            print("TLS configurado.")
        except Exception as e:
            print(f"Erro ao configurar TLS para MQTT: {e}. A conexão pode falhar.")
            # return None # Você pode descomentar isso se TLS for obrigatório

    # Define os Callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Tenta conectar
    try:
        print(f"Tentando conectar ao Broker MQTT: {mqtt_broker}:{mqtt_port}...")
        client.connect(mqtt_broker, mqtt_port, 60) # Timeout de 60s
        return client # Retorna o cliente configurado mas não em loop
    except ConnectionRefusedError:
         print(f"Erro: Conexão MQTT recusada. Verifique o broker ({mqtt_broker}) e porta ({mqtt_port}).")
         return None
    except OSError as e:
         print(f"Erro de Rede/OS ao conectar ao MQTT: {e}")
         return None
    except Exception as e:
        print(f"Erro inesperado ao conectar ao broker MQTT: {e}")
        return None

# --- Função Principal ---
def main():
    """Função principal para iniciar o listener MQTT."""
    print("Iniciando MQTT Listener...")
    client = configurar_mqtt() # Chama a função correta para configurar

    if client:
        print("Iniciando loop MQTT...")
        try:
            # Inicia o loop em uma thread separada para não bloquear
            # Isso também lida com reconexão automática
            client.loop_forever()
        except KeyboardInterrupt:
            print("\nInterrupção recebida. Encerrando MQTT Listener...")
        except Exception as e:
            print(f"Erro inesperado no loop principal do MQTT: {e}")
        finally:
            if client:
                print("Desconectando do broker MQTT...")
                client.disconnect() # Tenta desconectar graciosamente
                print("Cliente MQTT desconectado.")
    else:
        print("Falha ao configurar ou conectar o cliente MQTT. Encerrando.")

    print("Programa MQTT Listener finalizado.")

# --- Ponto de Entrada ---
if __name__ == "__main__":
    main()