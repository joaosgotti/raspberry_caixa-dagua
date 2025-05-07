# mqtt_listener.py
import paho.mqtt.client as mqtt
import ssl
import config
import json
import os
from datetime import datetime
from database_handler import DatabaseHandler # Importa nosso handler

class MQTTListener:
    """Classe simplificada para escutar MQTT e chamar o DB Handler."""

    def __init__(self, db_handler: DatabaseHandler):
        """
        Inicializa o MQTT Listener.

        Args:
            db_handler (DatabaseHandler): Uma instância do DatabaseHandler para persistir os dados.
        """
        self.db_handler = db_handler
        self.client_id = f"listener_pi_{os.getpid()}"
        print(f"[Listener] Criando cliente: {self.client_id}")
        # clean_session=True: Garante que as inscrições sejam feitas após cada conexão
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311, clean_session=True)
        self._configure_client()
        self.is_connected = False

    def _configure_client(self):
        """Configura autenticação, TLS (se necessário) e callbacks do cliente MQTT."""
        print("[Listener] Configurando auth/TLS...")
        self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
        if config.MQTT_PORT == 8883:
            try:
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[Listener] TLS habilitado.")
            except AttributeError:
                print("[Listener] Aviso: Módulo 'ssl' não encontrado. Conexão TLS não será estabelecida.")
            except Exception as e:
                print(f"[Listener] Erro ao configurar TLS: {e}")

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback chamado quando a conexão com o broker MQTT é estabelecida.
        Realiza a inscrição no tópico configurado.
        """
        if rc == 0:
            print("[Listener] Conectado ao Broker!")
            self.is_connected = True
            print(f"[Listener] Inscrevendo em '{config.MQTT_TOPIC}' com QoS 1...")
            res, mid = client.subscribe(config.MQTT_TOPIC, qos=1)
            if res != mqtt.MQTT_ERR_SUCCESS:
                print(f"[Listener] Falha ao inscrever: Código {res} - {mqtt.error_string(res)}")
        else:
            print(f"[Listener] Falha na conexão: Código {rc} - {mqtt.connack_string(rc)}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback chamado quando a conexão com o broker MQTT é perdida."""
        self.is_connected = False
        print(f"[Listener] Desconectado: Código {rc} - {mqtt.error_string(rc)}")
        if rc != 0:
            print("[Listener] Desconexão inesperada...")

    def _on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """Callback chamado após a inscrição em um tópico ser bem-sucedida."""
        print(f"[Listener] Inscrito (MID:{mid}) com QoS: {granted_qos}")

    def _on_message(self, client, userdata, msg):
        """
        Callback chamado quando uma mensagem é recebida no tópico inscrito.
        Decodifica o payload JSON e chama o DatabaseHandler para inserir os dados.
        """
        print(f"\n[Listener] Mensagem Recebida (Tópico: {msg.topic})")
        try:
            payload_str = msg.payload.decode('utf-8')
            print(f"  Payload: {payload_str}")
            data = json.loads(payload_str)

            if "distancia" in data and "created_on" in data:
                try:
                    distancia = float(data["distancia"])
                    created_on_str = data["created_on"]
                    created_on_dt = datetime.fromisoformat(created_on_str)
                    print("  -> Tentando inserir leitura no banco de dados...")
                    self.db_handler.insert_reading(distancia, created_on_dt) # Chama método do DB Handler
                except (ValueError, TypeError) as e:
                    print(f"  ERRO: Formato inválido nos dados recebidos: {e}")
                except Exception as e:
                    print(f"  ERRO inesperado ao processar os dados da mensagem: {e}")
            else:
                print("  ERRO: Payload JSON não contém as chaves 'distancia' ou 'created_on'.")
        except json.JSONDecodeError:
            print(f"  ERRO: Falha ao decodificar o payload JSON.")
        except Exception as e:
            print(f"  ERRO inesperado ao processar a mensagem MQTT: {e}")

    def connect(self):
        """Tenta conectar ao broker MQTT."""
        try:
            print(f"[Listener] Conectando a {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.MQTT_KEEPALIVE)
            return True
        except Exception as e:
            print(f"[Listener] ERRO ao conectar: {e}")
            return False

    def start_listening(self):
        """
        Inicia o loop principal de escuta do MQTT.
        Este método é bloqueante e manterá o listener em execução até que ocorra uma interrupção.
        """
        print("[Listener] Iniciando loop principal de escuta (loop_forever)...")
        try:
            # loop_forever lida com a rede MQTT, incluindo reconexões automáticas
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\n[Listener] Interrupção recebida (Ctrl+C). Encerrando...")
        except Exception as e:
            print(f"[Listener] ERRO CRÍTICO no loop principal (loop_forever): {e}")
        finally:
            print("[Listener] Saindo do loop.")

    def disconnect(self):
        """Desconecta o cliente MQTT do broker."""
        print("[Listener] Desconectando...")
        try:
            self.client.disconnect()
            print("[Listener] Desconectado.")
        except Exception as e:
            print(f"[Listener] Erro ao desconectar: {e}")

if __name__ == "__main__":
    # Este bloco é apenas para testes rápidos e não deve ser a forma principal de execução.
    # O main_listener.py é o script principal para iniciar o listener.
    import time
    import config
    from database_handler import DatabaseHandler

    if config.check_db_config_present():
        db_handler = DatabaseHandler()
        listener = MQTTListener(db_handler=db_handler)
        if listener.connect():
            try:
                listener.start_listening()
            finally:
                listener.disconnect()
        else:
            print("Falha ao conectar, encerrando.")
    else:
        print("Configurações de banco de dados ausentes, encerrando.")