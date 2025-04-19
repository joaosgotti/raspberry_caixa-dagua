import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime # OK
import json                   # OK
import os                     # OK
import ssl                   # OK

# dotenv import load_dotenv  # <-- TYPO AQUI!
from dotenv import load_dotenv # <-- CORREÇÃO

load_dotenv() # OK

# -----------------------------------------------------
# FUNÇÃO connect_db (Definida mas não chamada diretamente aqui, é chamada em on_message)
# Esta função parece CORRETA (usa env vars)
def connect_db():
    # ...(código da função connect_db que usa os.getenv)...
    # Verifica se as variáveis mais críticas foram definidas
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")

    required_vars = { # ... (verificação de vars) ... }
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        # ... (print erro e return None) ...
        print(f"Erro Crítico: Variáveis de ambiente do banco de dados ausentes: {', '.join(missing_vars)}")
        return None

    try:
        # ... (tentativa de conexão com logs) ...
        print(f"Tentando conectar ao DB: host={db_host}, db={db_name}, user={db_user}...") # Log útil
        connection = psycopg2.connect(
            dbname=db_name, user=db_user, password=db_password, host=db_host, port=db_port
        )
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except psycopg2.OperationalError as e:
        # ... (print erro e return None) ...
        print(f"Erro OPERACIONAL ao conectar ao banco de dados: {e}")
        return None
    except psycopg2.Error as e:
        # ... (print erro e return None) ...
        print(f"Erro psycopg2 ao conectar ao banco de dados: {e}")
        return None
    except Exception as e:
         # ... (print erro e return None) ...
         print(f"Erro INESPERADO durante a conexão com o banco de dados: {e}")
         return None
# -----------------------------------------------------

# -----------------------------------------------------
# FUNÇÃO configurar_mqtt (Versão CORRETA com env vars e TLS - Definida no TOPO)
# Esta função parece CORRETA
def configurar_mqtt():
    """
    Configures and connects the MQTT client using credentials from environment variables...
    """
    # ... (código da função configurar_mqtt que usa os.getenv e client.tls_set) ...
    mqtt_broker = os.getenv("MQTT_BROKER")
    try: # ... (pega porta) ...
        mqtt_port = int(os.getenv("MQTT_PORT", "8883"))
    except ValueError:
        print("Aviso: MQTT_PORT inválida no ambiente, usando porta padrão 8883.")
        mqtt_port = 8883
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")

    required_vars = { # ... (verificação de vars) ... }
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        # ... (print erro e return None) ...
        print(f"Erro Crítico: Variáveis de ambiente do MQTT ausentes: {', '.join(missing_vars)}")
        return None

    client_id = f"mqtt_listener_{os.getpid()}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.username_pw_set(mqtt_user, mqtt_password)

    if mqtt_port == 8883:
        try: # ... (configura TLS) ...
            print(f"Configurando TLS para conexão MQTT na porta {mqtt_port}...")
            client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
            print("TLS configurado.")
        except Exception as e:
            print(f"Erro ao configurar TLS para MQTT: {e}")
    else:
        print(f"Aviso: Conectando ao MQTT na porta {mqtt_port} sem TLS explícito.")

    client.on_connect = on_connect # OK
    client.on_message = on_message # OK (Importante que on_message esteja definida)
    client.on_disconnect = on_disconnect # OK

    try: # ... (tenta conectar) ...
        print(f"Tentando conectar ao Broker MQTT: {mqtt_broker}:{mqtt_port}...")
        client.connect(mqtt_broker, mqtt_port, 60)
        return client
    except ConnectionRefusedError: # ... (erros) ...
         print(f"Erro: Conexão MQTT recusada...")
         return None
    except OSError as e: # ... (erros) ...
         print(f"Erro de Rede/OS ao conectar ao MQTT: {e}")
         return None
    except Exception as e: # ... (erros) ...
        print(f"Erro inesperado ao conectar ao broker MQTT: {e}")
        return None
# -----------------------------------------------------

# --- Callbacks MQTT ---
# on_connect: Parece CORRETO (inscreve após conectar)
def on_connect(client, userdata, flags, rc, properties=None): # OK
    if rc == 0:
        print(f"Conectado ao Broker MQTT com sucesso (Código: {rc})")
        topic = "sensor/distancia"
        try:
            client.subscribe(topic)
            print(f"Inscrito no tópico: {topic}")
        except Exception as e:
            print(f"Erro ao se inscrever no tópico {topic}: {e}")
    else:
        print(f"Falha na conexão com o Broker MQTT (Código: {rc})...")

# on_message: Parece CORRETO (decodifica, processa, conecta db, insere, fecha)
def on_message(client, userdata, message):
    payload_str = ""
    try: # ... (decodifica) ...
        payload_str = message.payload.decode('utf-8')
        print(f"Mensagem recebida no tópico {message.topic}: {payload_str}")
    except UnicodeDecodeError as e: # ... (erro decode) ...
        print(f"Erro ao decodificar payload: {e}")
        return

    distancia, timestamp = processar_mensagem(payload_str) # OK

    if distancia is not None and timestamp is not None:
        connection = connect_db() # OK (Usa a função connect_db definida acima)
        if connection:
            cursor = None
            try:
                cursor = connection.cursor()
                inserir_leitura(cursor, distancia, timestamp) # OK (Usa a função inserir_leitura)
            except Exception as e_db:
                print(f"Erro durante operação com banco de dados: {e_db}")
            finally: # OK (fecha cursor e conexão)
                if cursor: cursor.close()
                if connection: connection.close()
                # Removi o print aqui para não poluir muito o log
    else:
        print("Falha ao processar a mensagem, dados não inseridos.")

# on_disconnect: OK
def on_disconnect(client, userdata, rc, properties=None): # OK
     if rc != 0: print(f"Desconexão inesperada do MQTT...")
     else: print("Desconectado do MQTT normalmente.")
# --- Fim Callbacks ---

# --- Funções Auxiliares ---
# inserir_leitura: Parece CORRETO
def inserir_leitura(cursor, distancia, timestamp):
    try:
        # ... (código INSERT) ...
        cursor.execute("INSERT INTO leituras (distancia, timestamp) VALUES (%s, %s);", (distancia, timestamp))
        cursor.connection.commit()
        print(f"Leitura inserida: Distancia={distancia} cm, Timestamp={timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    except psycopg2.Error as e:
        # ... (print erro e rollback) ...
        print(f"Erro ao inserir leitura: {e}")
        if cursor and cursor.connection: cursor.connection.rollback()

# processar_mensagem: Parece CORRETO (usa fromisoformat)
def processar_mensagem(payload_str):
    try:
        # ... (código json.loads, fromisoformat, validação) ...
        dados = json.loads(payload_str)
        distancia = dados['distancia']
        timestamp_str = dados['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str)
        if not isinstance(distancia, (int, float)): raise ValueError(...)
        if not isinstance(timestamp, datetime): raise ValueError(...)
        return distancia, timestamp
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        # ... (print erro e return None) ...
        print(f"Erro ao processar a mensagem: {e}")
        print(f"Payload problemático: {payload_str}")
        return None, None
    except Exception as e:
        # ... (print erro e return None) ...
        print(f"Erro inesperado ao processar mensagem: {e}")
        print(f"Payload problemático: {payload_str}")
        return None, None
# --- Fim Funções Auxiliares ---

# -----------------------------------------------------
# !!! PROBLEMA AQUI !!!
# Esta função configurar_mqtt está definida NOVAMENTE e está ERRADA!
# Ela usa valores fixos e não configura TLS.
# Ela será chamada pelo main() abaixo, ignorando a função correta definida no topo.
# def configurar_mqtt():
#     # Adicionar client_id é uma boa prática, especialmente se você tiver múltiplos listeners/publishers
#     client = mqtt.Client(client_id="mqtt_listener_caixa_dagua")
#     client.on_message = on_message
#
#     try:
#         # Substitua pelo IP correto da sua Raspberry Pi onde o broker Mosquitto está rodando
#         client.connect("192.168.0.49", 1883, 60) # <<< ERRADO para nuvem
#         client.subscribe("sensor/distancia")  # Inscreva-se no tópico
#         print("Conectado ao broker MQTT e pronto para receber mensagens.")
#     except Exception as e:
#         print(f"Erro ao conectar ao broker MQTT: {e}")
#         return None
#     return client
# -----------------------------------------------------

# Função principal para iniciar o cliente MQTT
def main():
    print("Iniciando MQTT Listener...")
    # Esta chamada usará a ÚLTIMA definição de configurar_mqtt (a errada!)
    client = configurar_mqtt() # <--- VAI CHAMAR A FUNÇÃO ERRADA
    if client:
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            # ... (código de parada) ...
            print("\nMQTT Listener encerrado pelo usuário.")
        except Exception as e:
            print(f"Erro inesperado no loop do MQTT: {e}")
        finally:
            # ... (código de desconexão) ...
            if client:
                print("Desconectando do broker MQTT...")
                client.disconnect()
                print("Cliente MQTT desconectado.")
    else:
        print("Não foi possível iniciar o cliente MQTT.")
    print("Programa finalizado.")

if __name__ == "__main__":
    main() # OK