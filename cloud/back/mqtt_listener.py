import psycopg2
import paho.mqtt.client as mqtt
from datetime import datetime # datetime já estava importado, ótimo!
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
        print(f"Leitura inserida: Distancia={distancia} cm, Timestamp={timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}") # Log formatado
    except psycopg2.Error as e:
        print(f"Erro ao inserir leitura: {e}")
        # Em caso de erro, é bom fazer rollback se a transação não foi completada
        if cursor and cursor.connection:
            cursor.connection.rollback()


# Função para processar a mensagem recebida (MODIFICADA)
def processar_mensagem(payload_str): # Recebe a string já decodificada
    """
    Processa o payload JSON recebido via MQTT.

    Args:
        payload_str (str): O payload da mensagem MQTT já decodificado como string.

    Returns:
        tuple: Uma tupla contendo (distancia, timestamp) se o processamento
               for bem-sucedido, caso contrário (None, None).
               Timestamp é um objeto datetime.
    """
    try:
        dados = json.loads(payload_str)

        # Extrai os dados
        distancia = dados['distancia']
        timestamp_str = dados['timestamp'] # Pega a string do timestamp

        # --- MODIFICAÇÃO AQUI ---
        # Converte a string ISO 8601 para um objeto datetime
        timestamp = datetime.fromisoformat(timestamp_str)
        # --- FIM DA MODIFICAÇÃO ---

        # Validação adicional (opcional, mas boa prática)
        if not isinstance(distancia, (int, float)):
            raise ValueError(f"Distancia recebida não é um número: {distancia}")
        if not isinstance(timestamp, datetime):
             raise ValueError("Timestamp não pôde ser convertido para datetime.")

        return distancia, timestamp

    except (KeyError, ValueError, json.JSONDecodeError) as e: # UnicodeDecodeError não é mais necessário aqui
        print(f"Erro ao processar a mensagem: {e}")
        print(f"Payload problemático: {payload_str}") # Loga a string que causou o problema
        return None, None
    except Exception as e:
        # Captura qualquer outro erro inesperado
        print(f"Erro inesperado ao processar mensagem: {e}")
        print(f"Payload problemático: {payload_str}")
        return None, None

# Função callback para quando uma mensagem MQTT for recebida
def on_message(client, userdata, message):
    # Decodifica a mensagem de bytes para string aqui
    payload_str = "" # Inicializa para o caso de falha na decodificação
    try:
        payload_str = message.payload.decode('utf-8')
        print(f"Mensagem recebida no tópico {message.topic}: {payload_str}")
    except UnicodeDecodeError as e:
        print(f"Erro ao decodificar payload: {e}")
        print(f"Payload (bytes): {message.payload}")
        return # Sai se não puder decodificar

    distancia, timestamp = processar_mensagem(payload_str) # Passa a string decodificada

    if distancia is not None and timestamp is not None:
        # Conectar ao banco de dados e inserir a leitura
        connection = connect_db()
        if connection:
            cursor = None # Inicializa cursor
            try:
                cursor = connection.cursor()
                inserir_leitura(cursor, distancia, timestamp)
            except Exception as e_db: # Captura exceções durante a operação de DB
                print(f"Erro durante operação com banco de dados: {e_db}")
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
                print("Conexão com o banco de dados fechada.")
    else:
        print("Falha ao processar a mensagem, dados não inseridos.")


# Configuração do cliente MQTT
def configurar_mqtt():
    # Adicionar client_id é uma boa prática, especialmente se você tiver múltiplos listeners/publishers
    client = mqtt.Client(client_id="mqtt_listener_caixa_dagua")
    client.on_message = on_message

    try:
        # Substitua pelo IP correto da sua Raspberry Pi onde o broker Mosquitto está rodando
        client.connect("192.168.0.49", 1883, 60) # A porta padrão do Mosquitto é 1883
        client.subscribe("sensor/distancia")  # Inscreva-se no tópico
        print("Conectado ao broker MQTT e pronto para receber mensagens.")
    except Exception as e:
        print(f"Erro ao conectar ao broker MQTT: {e}")
        return None
    return client

# Função principal para iniciar o cliente MQTT
def main():
    print("Iniciando MQTT Listener...")
    client = configurar_mqtt()
    if client:
        try:
            client.loop_forever()  # Loop para manter o cliente MQTT funcionando
        except KeyboardInterrupt:
            print("\nMQTT Listener encerrado pelo usuário.")
        except Exception as e:
            print(f"Erro inesperado no loop do MQTT: {e}")
        finally:
            if client:
                print("Desconectando do broker MQTT...")
                client.disconnect()
                print("Cliente MQTT desconectado.")
    else:
        print("Não foi possível iniciar o cliente MQTT.")
    print("Programa finalizado.")


if __name__ == "__main__":
    main()