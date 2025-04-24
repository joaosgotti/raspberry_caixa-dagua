# mqtt_listener_logic.py
import ssl
import os
import json
from datetime import datetime
import time
from typing import Optional, Tuple, Any # Usar Any se não importar DatabaseHandler
import sys

import config # Configurações MQTT e Tópico

# Comente/Remova a linha abaixo se você NÃO for usar o banco de dados de jeito nenhum
# Se for usar depois, mantenha e ajuste o tipo em __init__
from db_handler import DatabaseHandler # Para interagir com o DB

# --- Dependências Externas ---
try:
    import paho.mqtt.client as mqtt
except ImportError as e:
     print(f"Erro: Dependência paho-mqtt não encontrada - {e}")
     print("Instale: pip install paho-mqtt")
     sys.exit(1)


class MQTTListener:
    """Escuta mensagens MQTT e as processa (opcionalmente usando um DatabaseHandler)."""

    # Modificado para aceitar db_handler opcional
    def __init__(self, db_handler: Optional[DatabaseHandler] = None): # Ou Optional[Any] se comentou o import
        """
        Inicializa o listener MQTT.

        Args:
            db_handler: Uma instância opcional de DatabaseHandler para persistir os dados.
        """
        # Adiciona verificação de tipo apenas se db_handler for fornecido
        if db_handler is not None and not isinstance(db_handler, DatabaseHandler):
             raise TypeError("db_handler deve ser uma instância de DatabaseHandler")

        self.db_handler = db_handler
        self.client_id = f"mqtt_listener_{os.getpid()}"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.is_connected = False

        self._configure_client()
        print("[MQTT Listener] Instância criada.")
        if self.db_handler is None:
            print("[MQTT Listener] Rodando em modo TESTE (sem interação com Banco de Dados).")

    def _configure_client(self):
        """Configura autenticação, TLS e callbacks para o cliente MQTT."""
        try:
            # Verifica se usuário e senha foram definidos no config (evita erro se estiverem vazios)
            if config.MQTT_USER and config.MQTT_PASSWORD:
                self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
                print("[MQTT Listener] Usuário/Senha definidos.")
            elif config.MQTT_USER:
                 print("[MQTT Listener] Apenas usuário MQTT definido (sem senha).")
                 self.client.username_pw_set(config.MQTT_USER)
            else:
                print("[MQTT Listener] Conectando sem usuário/senha MQTT.")


            if config.MQTT_PORT == 8883:
                print("[MQTT Listener] Configurando TLS...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                # Opcional: Adicionar para depurar problemas de certificado (se aplicável)
                # self.client.tls_insecure_set(True) # APENAS PARA TESTE, NÃO USE EM PRODUÇÃO
                print("[MQTT Listener] TLS configurado.")
            else:
                print("[MQTT Listener] Conexão sem TLS (porta diferente de 8883).")

            # Atribuição dos Callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            # self.client.on_log = self._on_log # Descomente para debug MUITO detalhado

        except Exception as e:
            print(f"[MQTT Listener] Erro ao configurar cliente MQTT: {e}")
            raise

    # def _on_log(self, client, userdata, level, buf):
    #      # Callback de Log para Debug Detalhado
    #      print(f"[MQTT LOG | Level:{level}] {buf}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback executado quando a conexão MQTT é estabelecida ou falha."""
        # DEBUG: Imprime o código de retorno sempre
        print(f"[MQTT Listener] Callback _on_connect chamado com código de retorno (rc): {rc}")

        if rc == 0:
            self.is_connected = True
            print(f"[MQTT Listener] Conectado ao Broker MQTT com sucesso!")
            try:
                print(f"[MQTT Listener] Inscrevendo-se no tópico: {config.MQTT_TOPIC}")
                # Inscrever com QoS 1 para garantir a entrega da inscrição
                result, mid = client.subscribe(config.MQTT_TOPIC, qos=1)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT Listener] Inscrito com sucesso no tópico '{config.MQTT_TOPIC}' (MID: {mid})")
                else:
                    print(f"[MQTT Listener] Falha ao inscrever no tópico '{config.MQTT_TOPIC}', erro MQTT: {mqtt.error_string(result)}")
            except Exception as e:
                print(f"[MQTT Listener] Erro EXCEPCIONAL durante a inscrição no tópico '{config.MQTT_TOPIC}': {e}")
        else:
            self.is_connected = False
            # Imprime o erro específico baseado no código rc
            error_message = mqtt.connack_string(rc) # Usa função da Paho para descrever o erro
            print(f"[MQTT Listener] Falha na conexão com o Broker MQTT (Código: {rc}) - {error_message}")
            print("[MQTT Listener] -> Verifique: Endereço/Porta do Broker, Credenciais (usuário/senha), Configuração TLS, Rede/Firewall, Status do Broker.")
            # Se a falha for de autorização, talvez seja útil parar o cliente para evitar loops de reconexão
            if rc in [mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD, mqtt.CONNACK_REFUSED_NOT_AUTHORIZED]:
                 print("[MQTT Listener] Erro de autenticação/autorização detectado. Interrompendo tentativas futuras.")
                 # Considerar chamar self.client.disconnect() ou self.client.loop_stop() aqui se o loop_forever estiver ativo
                 # No setup atual com main_listener.py, o fluxo já vai parar.

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback executado quando a conexão MQTT é perdida."""
         # DEBUG: Imprime o código de retorno sempre
        print(f"[MQTT Listener] Callback _on_disconnect chamado com código de retorno (rc): {rc}")
        self.is_connected = False
        if rc == 0:
             print("[MQTT Listener] Desconexão limpa iniciada pelo cliente.")
        else:
            print(f"[MQTT Listener] Desconectado INESPERADAMENTE do MQTT (Código: {rc}). Razão: {mqtt.error_string(rc)}")
            print("[MQTT Listener] -> Verifique a rede, o status do broker. A biblioteca tentará reconectar automaticamente se estiver usando loop_start/loop_forever.")

    def _process_message(self, payload_str: str) -> Optional[Tuple[float, datetime]]:
        """
        Processa o payload da mensagem JSON recebida, esperando 'distancia' e 'created_on'.

        Args:
            payload_str: O payload da mensagem como string UTF-8.

        Returns:
            Uma tupla (distancia, created_on_dt) ou None se falhar.
        """
        try:
            dados = json.loads(payload_str)
            # Validação explícita das chaves
            if 'distancia' not in dados or 'created_on' not in dados:
                raise KeyError("Chaves 'distancia' ou 'created_on' ausentes no JSON.")

            distancia = dados['distancia']
            created_on_str = dados['created_on']

            # Conversão e Validação mais robusta
            distancia_float = float(distancia)
            created_on_dt = datetime.fromisoformat(created_on_str) # Espera formato ISO 8601

            return distancia_float, created_on_dt

        except json.JSONDecodeError as e:
             print(f"  [MQTT Listener] Erro ao decodificar JSON: {e}")
             print(f"  Payload recebido: {payload_str}")
             return None
        except KeyError as e:
             print(f"  [MQTT Listener] Erro no conteúdo do JSON: {e}")
             print(f"  Payload recebido: {payload_str}")
             return None
        except (ValueError, TypeError) as e:
             print(f"  [MQTT Listener] Erro de valor ou tipo ao processar dados do JSON: {e}")
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
            print(f"\n[MQTT Listener] Mensagem recebida | Tópico: {message.topic} | QoS: {message.qos} | Retain: {message.retain}")
            # print(f"  Payload Raw: {payload_str}") # Descomente se precisar ver o JSON cru sempre
        except UnicodeDecodeError as e:
            print(f"\n[MQTT Listener] Erro ao decodificar payload (não UTF-8?) | Tópico: {message.topic} | Erro: {e}")
            #print(f"  Payload Raw (bytes): {message.payload}")
            return # Ignora mensagem malformada

        # Processa a mensagem para extrair dados
        processed_data = self._process_message(payload_str)

        if processed_data:
            distancia, created_on_dt = processed_data
            print(f"  Dados processados: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S%z')}") # Inclui timezone se houver

            # --- Interação com o Banco de Dados (Condicional) ---
            if self.db_handler:
                print("  [MQTT Listener] Tentando interação com o Banco de Dados...")
                connection = None # Garante que connection seja definida
                try:
                    connection = self.db_handler.connect()
                    if connection:
                        success = self.db_handler.insert_reading(connection, distancia, created_on_dt)
                        if not success:
                            print("  [MQTT Listener] Falha ao inserir dados no banco (ver logs do DB Handler).")
                        # Se sucesso, a msg já é impressa pelo db_handler
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
                 # A mensagem de modo teste já foi impressa no __init__
                 # print("  [MQTT Listener] Banco de dados desativado para este teste.")
                 pass # Não faz nada com o DB
            # --- Fim da Interação com o Banco de Dados ---
        else:
            print(f"  [MQTT Listener] Falha ao processar mensagem JSON. Payload: {payload_str}")


    def connect(self) -> bool:
        """Tenta iniciar a conexão com o broker MQTT."""
        if self.is_connected:
             print("[MQTT Listener] Já está conectado.")
             return True

        try:
            print(f"[MQTT Listener] Tentando conectar ao Broker MQTT: {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            # O connect é assíncrono, o resultado real vem no callback _on_connect
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60) # Keepalive 60s
            print("[MQTT Listener] Comando connect enviado. Aguardando callback _on_connect...")
            return True # Indica que a tentativa foi iniciada sem erro imediato
        except ssl.SSLError as e:
             print(f"[MQTT Listener] Erro SSL ao tentar conectar: {e}")
             print(" -> Verifique configuração TLS, certificados (se aplicável) e compatibilidade com o broker.")
             return False
        except OSError as e:
             print(f"[MQTT Listener] Erro de Rede/OS ao tentar conectar: {e}")
             print(" -> Verifique conectividade de rede, DNS, firewall e se o endereço/porta do broker está correto.")
             return False
        except Exception as e:
            print(f"[MQTT Listener] Erro inesperado ao iniciar conexão com broker MQTT: {e}")
            return False

    def start_listening(self):
        """Inicia o loop principal para escutar mensagens MQTT (bloqueante)."""
        if not self.is_connected:
             print("[MQTT Listener] ERRO: Não pode iniciar loop de escuta sem estar conectado.")
             return

        print("[MQTT Listener] Iniciando loop de escuta MQTT (blocking - use Ctrl+C para sair)...")
        try:
            # loop_forever() é bloqueante e lida com reconexões automaticamente (se não for erro fatal como auth)
            self.client.loop_forever()
        except KeyboardInterrupt:
             # Permitir que o KeyboardInterrupt seja tratado no main_listener
             print("\n[MQTT Listener] KeyboardInterrupt recebido no loop_forever.")
             # O finally no main_listener chamará disconnect()
        except Exception as e:
             print(f"[MQTT Listener] Erro crítico dentro do loop_forever: {e}")
             # Pode ser útil tentar desconectar aqui também antes de sair
             self.disconnect()
        finally:
            print("[MQTT Listener] Saindo do loop_forever.")


    def disconnect(self):
        """Desconecta o cliente MQTT."""
        if self.client and self.client.is_connected():
            print("[MQTT Listener] Desconectando cliente MQTT...")
            self.client.disconnect() # Solicita desconexão limpa
            # Não é necessário loop_stop() se usou loop_forever(), a interrupção já parou o loop.
            # Se usasse loop_start(), seria necessário self.client.loop_stop() aqui.
            print("[MQTT Listener] Comando de desconexão enviado.")
        else:
            print("[MQTT Listener] Cliente não estava conectado ou já desconectado.")
        # Garante que o estado seja atualizado
        self.is_connected = False