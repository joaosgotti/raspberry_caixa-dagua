# mqtt_publisher.py
import paho.mqtt.client as mqtt
import ssl
import os
import json
import datetime
import time # Para sleep
import config # Importa as configurações MQTT

class MQTTHandler:
    """Classe para gerenciar a comunicação MQTT (Publicação)."""

    def __init__(self):
        """Inicializa o cliente MQTT e configura callbacks e segurança."""
        self.client_id = f"{config.CLIENT_ID_PREFIX}{os.getpid()}"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.is_connected = False

        # Define os callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish # Opcional, para debug

        # Configura Autenticação e TLS
        print(f"[MQTT Publisher] Configurando conexão para {config.MQTT_BROKER}:{config.MQTT_PORT}...")
        try:
            self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
            print("[MQTT Publisher] Usuário/Senha definidos.")

            if config.MQTT_PORT == 8883:
                print("[MQTT Publisher] Configurando TLS...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[MQTT Publisher] TLS configurado.")
            else:
                 print("[MQTT Publisher] TLS não configurado (porta diferente de 8883).")

        except Exception as e:
            print(f"[MQTT Publisher] Erro ao configurar autenticação ou TLS: {e}")
            raise

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback chamado quando a conexão com o broker é estabelecida."""
        if rc == 0:
            self.is_connected = True
            print("[MQTT Publisher] Conectado ao Broker com sucesso!")
        else:
            self.is_connected = False
            print(f"[MQTT Publisher] Falha na conexão, código de retorno={rc}")
            print("[MQTT Publisher] Verifique host, porta, usuário, senha e configuração TLS.")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback chamado quando o cliente é desconectado do broker."""
        self.is_connected = False
        print(f"[MQTT Publisher] Desconectado do broker (código: {rc}).")
        # loop_start() tenta reconectar automaticamente

    def _on_publish(self, client, userdata, mid):
        """Callback chamado após uma mensagem ser publicada (do ponto de vista do cliente)."""
        # print(f"  [MQTT Publisher] Mensagem (mid={mid}) publicada localmente.")
        pass

    def connect(self) -> bool:
        """Tenta conectar ao broker MQTT e inicia o loop em background."""
        try:
            print("[MQTT Publisher] Conectando ao broker...")
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60) # Keepalive de 60s
            self.client.loop_start() # Inicia a thread de rede em background
            print("[MQTT Publisher] Loop de rede iniciado.")
            # Dê um tempo para a conexão acontecer
            time.sleep(2) # Ajuste conforme necessário
            return self.is_connected
        except Exception as e:
            print(f"[MQTT Publisher] Erro fatal ao tentar conectar: {e}")
            print("[MQTT Publisher] Verifique as configurações e a conexão de rede.")
            self.is_connected = False
            return False

    def disconnect(self):
        """Para o loop de rede e desconecta do broker."""
        if self.is_connected: # Verifica se estava conectado antes de tentar parar/desconectar
            print("[MQTT Publisher] Desconectando...")
            self.client.loop_stop() # Para a thread de rede
            self.client.disconnect()
            self.is_connected = False # Garante que o estado seja atualizado
            print("[MQTT Publisher] Desconectado.")
        else:
            # Se loop_start foi chamado mas a conexão falhou, loop_stop ainda pode ser necessário
            try:
                 self.client.loop_stop(force=True)
            except Exception:
                 pass # Ignora erros ao parar loop se não estava ativo
            print("[MQTT Publisher] Já estava desconectado ou conexão falhou.")


    def publish_distancia(self, distancia: float):
        """
        Publica a medição de distância no tópico MQTT configurado.

        Args:
            distancia: O valor da distância a ser publicado (float).
        """
        if not self.is_connected:
            print("[MQTT Publisher] Não conectado. Publicação ignorada.")
            return

        payload = {
            "distancia": round(distancia), # Arredondado para inteiro
            "created_on": datetime.datetime.now().isoformat() # Timestamp no formato ISO
        }
        payload_json = json.dumps(payload)

        try:
            # Publica com QoS 1 (pelo menos uma entrega)
            result = self.client.publish(config.MQTT_TOPIC, payload_json, qos=1)
            # result.wait_for_publish(timeout=5.0) # Bloqueia (opcional)
            print(f"  -> [MQTT Publisher] Publicando (mid={result.mid}): {payload_json}")
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                 # Isso indica um erro antes mesmo de enviar (ex: fila cheia)
                 print(f"  -> [MQTT Publisher] Erro na publicação local (código={result.rc})")
        except Exception as e:
            print(f"  -> [MQTT Publisher] Erro ao tentar publicar: {e}")