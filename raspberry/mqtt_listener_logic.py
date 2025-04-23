# mqtt_listener_logic.py
import ssl
import os
import json
from datetime import datetime
import time
from typing import Optional, Tuple
import sys

import config # Configurações MQTT e Tópico
from db_handler import DatabaseHandler # Para interagir com o DB

# --- Dependências Externas ---
try:
    import paho.mqtt.client as mqtt
except ImportError as e:
     print(f"Erro: Dependência paho-mqtt não encontrada - {e}")
     print("Instale: pip install paho-mqtt")
     sys.exit(1)


class MQTTListener:
    """Escuta mensagens MQTT e as processa usando um DatabaseHandler."""

    def __init__(self, db_handler: DatabaseHandler):
        """
        Inicializa o listener MQTT.

        Args:
            db_handler: Uma instância de DatabaseHandler para persistir os dados.
        """
        if not isinstance(db_handler, DatabaseHandler):
             raise TypeError("db_handler deve ser uma instância de DatabaseHandler")
        self.db_handler = db_handler
        self.client_id = f"mqtt_listener_{os.getpid()}"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.is_connected = False

        self._configure_client()
        print("[MQTT Listener] Instância criada.")

    def _configure_client(self):
        """Configura autenticação, TLS e callbacks para o cliente MQTT."""
        try:
            self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
            print("[MQTT Listener] Usuário/Senha definidos.")

            if config.MQTT_PORT == 8883:
                print("[MQTT Listener] Configurando TLS...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[MQTT Listener] TLS configurado.")

            # Atribuição dos Callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            # self.client.on_log = self._on_log # Para debug avançado

        except Exception as e:
            print(f"[MQTT Listener] Erro ao configurar cliente MQTT: {e}")
            raise

    # def _on_log(self, client, userdata, level, buf):
    #      # Callback de Log para Debug Detalhado (descomente se necessário)
    #      print(f"[MQTT Log] level={level}, buf={buf}")
    #      pass

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback executado quando a conexão MQTT é estabelecida."""
        if rc == 0:
            self.is_connected = True
            print(f"[MQTT Listener] Conectado ao Broker MQTT com sucesso (Código: {rc})")
            try:
                print(f"[MQTT Listener] Inscrevendo-se no tópico: {config.MQTT_TOPIC}")
                result, mid = client.subscribe(config.MQTT_TOPIC, qos=1) # Usar QoS 1 na inscrição também
                if result == mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT Listener] Inscrito com sucesso (MID: {mid})")
                else:
                    print(f"[MQTT Listener] Falha ao inscrever no tópico {config.MQTT_TOPIC}, erro MQTT: {result}")
            except Exception as e:
                print(f"[MQTT Listener] Erro durante a inscrição no tópico {config.MQTT_TOPIC}: {e}")
        else:
            self.is_connected = False
            print(f"[MQTT Listener] Falha na conexão com o Broker MQTT (Código: {rc}) - Verifique credenciais/rede/broker.")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback executado quando a conexão MQTT é perdida."""
        self.is_connected = False
        print(f"[MQTT Listener] Desconectado do MQTT (Código: {rc}).")
        if rc != 0:
            print("[MQTT Listener] Desconexão inesperada. O loop tentará reconectar...")

    def _process_message(self, payload_str: str) -> Optional[Tuple[float, datetime]]:
        """
        Processa o payload da mensagem JSON recebida, esperando 'created_on'.

        Args:
            payload_str: O payload da mensagem como string UTF-8.

        Returns:
            Uma tupla (distancia, created_on_dt) ou None.
        """
        try:
            dados = json.loads(payload_str)
            distancia = dados['distancia']
            created_on_str = dados['created_on'] # Chave esperada do JSON

            # Conversão e Validação
            distancia_float = float(distancia) # Converte para float
            created_on_dt = datetime.fromisoformat(created_on_str)

            # Validação extra opcional (ex: limites razoáveis para distância)
            # if not (0 < distancia_float < 500): # Exemplo
            #     raise ValueError(f"Distancia ({distancia_float}) fora dos limites esperados.")

            return distancia_float, created_on_dt

        except json.JSONDecodeError as e:
             print(f"  [MQTT Listener] Erro ao decodificar JSON: {e}")
             print(f"  Payload recebido: {payload_str}")
             return None
        except KeyError as e:
             print(f"  [MQTT Listener] Chave esperada não encontrada no JSON: {e} (Esperando 'distancia' e 'created_on')")
             print(f"  Payload recebido: {dados if 'dados' in locals() else payload_str}")
             return None
        except (ValueError, TypeError) as e:
             print(f"  [MQTT Listener] Erro de valor ou tipo ao processar dados: {e}")
             print(f"  Payload recebido: {payload_str}")
             return None
        except Exception as e:
            print(f"  [MQTT Listener] Erro inesperado ao processar mensagem: {e}")
            print(f"  Payload recebido: {payload_str}")
            return None

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage):
        """Callback executado quando uma mensagem MQTT é recebida."""
        try:
            payload_str = message.payload.decode('utf-8')
            print(f"\n[MQTT Listener] Mensagem recebida | Tópico: {message.topic} | QoS: {message.qos}")
        except UnicodeDecodeError as e:
            print(f"[MQTT Listener] Erro ao decodificar payload (não UTF-8?): {e}")
            #print(f"  Payload Raw: {message.payload}")
            return # Ignora mensagem malformada

        # Processa a mensagem para extrair dados
        processed_data = self._process_message(payload_str)

        if processed_data:
            distancia, created_on_dt = processed_data
            print(f"  Dados processados: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            # Tenta interagir com o banco de dados
            connection = None # Garante que connection seja definida
            try:
                connection = self.db_handler.connect()
                if connection:
                    success = self.db_handler.insert_reading(connection, distancia, created_on_dt)
                    if not success:
                        print("  [MQTT Listener] Falha ao inserir dados no banco (ver logs do DB Handler).")
                else:
                    # Log de falha na conexão já ocorre no db_handler
                    print("  [MQTT Listener] Falha ao conectar ao DB nesta tentativa. Dados não inseridos.")
            except Exception as db_err:
                 # Captura erros inesperados na lógica de conexão/inserção
                 print(f"  [MQTT Listener] Erro durante interação com DB: {db_err}")
            finally:
                # Garante que a conexão seja fechada se foi aberta
                if connection:
                    self.db_handler.close(connection)
        else:
            print("  [MQTT Listener] Falha ao processar mensagem. Dados não inseridos.")


    def connect(self) -> bool:
        """Tenta conectar ao broker MQTT."""
        try:
            print(f"[MQTT Listener] Tentando conectar ao Broker MQTT: {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60) # Keepalive 60s
            return True # A conexão real é confirmada no _on_connect
        except ssl.SSLError as e:
             print(f"[MQTT Listener] Erro SSL ao conectar: {e} - Verifique certificados ou configuração TLS.")
             return False
        except OSError as e:
             print(f"[MQTT Listener] Erro de Rede/OS ao conectar: {e} - Verifique conectividade/firewall.")
             return False
        except Exception as e:
            print(f"[MQTT Listener] Erro geral ao iniciar conexão com broker MQTT: {e}")
            return False

    def start_listening(self):
        """Inicia o loop principal para escutar mensagens MQTT."""
        print("[MQTT Listener] Iniciando loop de escuta MQTT (blocking)...")
        try:
            # loop_forever() é bloqueante e lida com reconexões automaticamente
            self.client.loop_forever()
        except KeyboardInterrupt:
             # Permitir que o KeyboardInterrupt seja tratado no main_listener
             print("\n[MQTT Listener] KeyboardInterrupt recebido no loop.")
             raise # Re-levanta para o bloco finally no main_listener
        except Exception as e:
             print(f"[MQTT Listener] Erro crítico dentro do loop_forever: {e}")
             # Pode ser útil tentar desconectar aqui também antes de sair
             self.disconnect()


    def disconnect(self):
        """Desconecta o cliente MQTT."""
        try:
            print("[MQTT Listener] Desconectando cliente MQTT...")
            # Não é necessário loop_stop() com loop_forever()
            self.client.disconnect()
            print("[MQTT Listener] Comando de desconexão enviado.")
        except Exception as e:
            print(f"[MQTT Listener] Erro ao tentar desconectar: {e}")