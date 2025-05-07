# mqtt_publisher.py
import paho.mqtt.client as mqtt
import ssl
import config
import json
import os
from datetime import datetime, timezone

class MQTTPublisher:
    """Classe para publicar mensagens MQTT."""

    def __init__(self):
        """Inicializa o cliente MQTT publisher."""
        self.client_id = f"publisher_pi_{os.getpid()}"
        print(f"[Publisher] Criando cliente: {self.client_id}")
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self._configure_client()
        self.is_connected = False

    def _configure_client(self):
        """Configura autenticação, TLS (se necessário) e callbacks."""
        print("[Publisher] Configurando auth/TLS...")
        self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
        if config.MQTT_PORT == 8883:
            try:
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[Publisher] TLS habilitado.")
            except AttributeError:
                print("[Publisher] Aviso: Módulo 'ssl' não encontrado. Conexão TLS não será estabelecida.")
            except Exception as e:
                print(f"[Publisher] Erro ao configurar TLS: {e}")

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback chamado quando a conexão com o broker é estabelecida."""
        if rc == 0:
            print("[Publisher] Conectado ao Broker!")
            self.is_connected = True
        else:
            print(f"[Publisher] Falha na conexão: Código {rc} - {mqtt.connack_string(rc)}")
            self.is_connected = False

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback chamado quando a conexão com o broker é perdida."""
        self.is_connected = False
        print(f"[Publisher] Desconectado: Código {rc} - {mqtt.error_string(rc)}")
        if rc != 0:
            print("[Publisher] Desconexão inesperada...")

    def connect(self):
        """Tenta conectar ao broker MQTT e inicia o loop de rede em background."""
        try:
            print(f"[Publisher] Conectando a {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.MQTT_KEEPALIVE)
            self.client.loop_start() # Executa a thread de rede para lidar com conexões e mensagens
            print("[Publisher] Loop de rede iniciado.")
            return True
        except Exception as e:
            print(f"[Publisher] ERRO ao conectar: {e}")
            return False

    def publish_data(self, data_dict):
        """
        Publica um dicionário de dados como uma mensagem JSON no tópico configurado.

        Args:
            data_dict (dict): O dicionário contendo os dados a serem publicados.

        Returns:
            bool: True se a publicação foi bem-sucedida, False caso contrário.
        """
        if not self.is_connected:
            print("[Publisher] Não conectado ao broker, pulando publicação.")
            return False

        try:
            payload_json = json.dumps(data_dict)
            result, mid = self.client.publish(config.MQTT_TOPIC, payload_json, qos=1)
            if result == mqtt.MQTT_ERR_SUCCESS:
                 print(f"  [Publisher] Publicado (MID:{mid}): {payload_json}")
                 return True
            else:
                 print(f"  [Publisher] Erro ao publicar: Código {result} - {mqtt.error_string(result)}")
                 return False
        except Exception as e:
            print(f"  [Publisher] ERRO ao publicar: {e}")