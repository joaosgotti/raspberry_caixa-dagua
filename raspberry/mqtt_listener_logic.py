# mqtt_listener_logic.py
# -*- coding: utf-8 -*-

import ssl
import os
import json
from datetime import datetime
import time
from typing import Optional, Tuple, Any # Usar Any se não importar DatabaseHandler
import sys

import config # Configurações MQTT e Tópico

# --- Interação com Banco de Dados (Opcional) ---
# Descomente a linha abaixo se você for usar o banco de dados.
# Certifique-se que db_handler.py existe e está correto.
# from db_handler import DatabaseHandler

# --- Dependências Externas ---
try:
    import paho.mqtt.client as mqtt
except ImportError as e:
     print(f"Erro CRÍTICO: Dependência paho-mqtt não encontrada - {e}")
     print("Por favor, instale com: pip install paho-mqtt")
     sys.exit(1)


class MQTTListener:
    """
    Escuta mensagens em um tópico MQTT, processa os dados recebidos (JSON esperado)
    e opcionalmente os persiste usando um DatabaseHandler.
    Inclui logging detalhado e lógica de re-inscrição no tópico após reconexão.
    """

    # Modificado para aceitar db_handler opcional
    def __init__(self, db_handler: Optional[Any] = None): # Use Optional[DatabaseHandler] se importou
        """
        Inicializa o listener MQTT.

        Args:
            db_handler: Uma instância opcional de DatabaseHandler para persistir os dados.
                        Se None, operará em modo de teste sem banco de dados.
        """
        # Valida db_handler apenas se ele for fornecido e o tipo for importado
        # if db_handler is not None and 'DatabaseHandler' in globals() and not isinstance(db_handler, DatabaseHandler):
        #      raise TypeError("db_handler deve ser uma instância de DatabaseHandler")

        self.db_handler = db_handler
        self.client_id = f"mqtt_listener_{os.getpid()}_{time.time():.0f}" # ID mais único
        print(f"[MQTT Listener] Usando Client ID: {self.client_id}")
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.is_connected = False

        self._configure_client() # Chama a configuração detalhada

        print("[MQTT Listener] Instância criada e cliente pré-configurado.")
        if self.db_handler is None:
            print("[MQTT Listener] *** MODO TESTE SEM BANCO DE DADOS ATIVADO ***")

    # --- Callbacks Paho MQTT ---

    def _on_log(self, client, userdata, level, buf):
        """Callback de Log para Debug Detalhado Paho."""
        # Imprime TODOS os níveis agora para diagnóstico
        print(f"[MQTT PAHO LOG | Lvl:{level}] {buf}")


    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback executado quando a conexão MQTT é estabelecida ou falha."""
        print(f"[MQTT Listener] Callback _on_connect chamado com código de retorno (rc): {rc}")

        if rc == 0:
            self.is_connected = True
            print(f"[MQTT Listener] CONECTADO com sucesso ao Broker MQTT!")

            # --- LÓGICA DE RE-INSCRIÇÃO ---
            # Sempre tenta (re)inscrever após uma conexão bem-sucedida
            try:
                topic = config.MQTT_TOPIC
                qos = 1
                print(f"[MQTT Listener] Tentando (RE)INSCREVER no tópico: '{topic}' com QoS {qos}...")
                # Faça a inscrição aqui
                result, mid = client.subscribe(topic, qos=qos)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT Listener] >> (Re)Inscrito com sucesso (MID: {mid})")
                else:
                    print(f"[MQTT Listener] ERRO ao (re)inscrever! Código Paho: {result} - {mqtt.error_string(result)}")
            except Exception as e:
                print(f"[MQTT Listener] ERRO EXCEPCIONAL durante a (re)inscrição no tópico '{topic}': {e}")
            # --- FIM DA LÓGICA DE RE-INSCRIÇÃO ---

        else:
            # A lógica de falha na conexão permanece a mesma
            self.is_connected = False
            error_message = mqtt.connack_string(rc)
            print(f"[MQTT Listener] FALHA NA CONEXÃO com Broker MQTT (Código: {rc}) - {error_message}")
            print("[MQTT Listener] -> VERIFIQUE: Endereço/Porta, Credenciais, TLS, Rede/Firewall, Status do Broker.")
            if rc in [mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD, mqtt.CONNACK_REFUSED_NOT_AUTHORIZED]:
                 print("[MQTT Listener] *** Erro crítico de autenticação/autorização. ***")


    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback executado quando a conexão MQTT é perdida."""
        print(f"[MQTT Listener] Callback _on_disconnect chamado com código de retorno (rc): {rc}")
        was_connected = self.is_connected # Guarda o estado anterior
        self.is_connected = False
        if rc == 0:
             print("[MQTT Listener] Desconexão limpa iniciada pelo cliente ou broker.")
        else:
            # Usar diretamente mqtt.error_string(rc)
            reason = mqtt.error_string(rc)
            print(f"[MQTT Listener] DESCONECTADO INESPERADAMENTE do MQTT (Código: {rc}). Razão: {reason}")
            if was_connected: # Só avisa sobre reconexão se estava conectado antes
                print("[MQTT Listener] -> Verifique a rede, o status do broker. Tentativa de reconexão automática (se aplicável)...")


    def _on_message(self, client, userdata, message: mqtt.MQTTMessage):
        """Callback executado quando uma mensagem MQTT é recebida."""
        try:
            payload_str = message.payload.decode('utf-8')
            print(f"\n[MQTT Listener] Mensagem recebida | Tópico: {message.topic} | QoS: {message.qos} | Retain: {message.retain}")
        except UnicodeDecodeError as e:
            print(f"\n[MQTT Listener] ERRO ao decodificar payload (não UTF-8?) | Tópico: {message.topic} | Erro: {e}")
            return # Ignora mensagem malformada

        # Processa a mensagem para extrair dados
        processed_data = self._process_message(payload_str)

        if processed_data:
            distancia, created_on_dt = processed_data
            print(f"  Dados processados: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S%z')}")

            # --- Interação com o Banco de Dados (Condicional) ---
            if self.db_handler:
                connection = None
                try:
                    connection = self.db_handler.connect()
                    if connection:
                        success = self.db_handler.insert_reading(connection, distancia, created_on_dt)
                        if not success:
                             print("  [MQTT Listener] Falha ao inserir no DB (ver logs do DB Handler).")
                    else:
                        print("  [MQTT Listener] Falha ao conectar ao DB nesta tentativa.")
                except Exception as db_err:
                     print(f"  [MQTT Listener] ERRO durante interação com DB: {db_err}")
                finally:
                    if connection:
                        self.db_handler.close(connection)
            # --- Fim da Interação com o Banco de Dados ---
        else:
            print(f"  [MQTT Listener] Falha ao processar JSON da mensagem. Payload: {payload_str}")

    # --- Métodos de Controle do Cliente ---

    def _configure_client(self):
        """Configura autenticação, TLS e todos os callbacks para o cliente MQTT."""
        print("[MQTT Listener] Configurando cliente Paho...")
        try:
            # 1. Autenticação
            if config.MQTT_USER and config.MQTT_PASSWORD:
                self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
                print("[MQTT Listener] Usando Usuário/Senha do config.py.")
            elif config.MQTT_USER:
                 print("[MQTT Listener] Usando apenas Usuário do config.py (sem senha).")
                 self.client.username_pw_set(config.MQTT_USER)
            else:
                print("[MQTT Listener] Conectando sem usuário/senha MQTT (config não definido).")

            # 2. Configuração TLS (se porta for 8883)
            if config.MQTT_PORT == 8883:
                print("[MQTT Listener] Configurando TLS (porta 8883 detectada)...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[MQTT Listener] TLS v1.2 configurado.")
            else:
                print("[MQTT Listener] Conexão sem TLS (porta diferente de 8883).")

            # 3. Atribuição dos Callbacks Essenciais
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # 4. Atribuição do Callback de Log Detalhado
            self.client.on_log = self._on_log
            print("[MQTT Listener] Callback de log interno Paho (_on_log) ativado.")

            print("[MQTT Listener] Configuração do cliente Paho finalizada.")

        except Exception as e:
            print(f"[MQTT Listener] ERRO CRÍTICO ao configurar cliente Paho MQTT: {e}")
            raise # Re-levanta a exceção para parar a inicialização

    def _process_message(self, payload_str: str) -> Optional[Tuple[float, datetime]]:
        """
        Processa o payload da mensagem JSON, esperando 'distancia' e 'created_on' (ISO format).

        Args:
            payload_str: O payload da mensagem como string UTF-8.
        Returns:
            Uma tupla (distancia_float, created_on_dt) ou None se falhar.
        """
        try:
            dados = json.loads(payload_str)
            if not isinstance(dados, dict):
                raise ValueError("Payload JSON não é um dicionário.")
            if 'distancia' not in dados or 'created_on' not in dados:
                raise KeyError("Chaves 'distancia' ou 'created_on' ausentes no JSON.")

            distancia = dados['distancia']
            created_on_str = dados['created_on']

            distancia_float = float(distancia)
            created_on_dt = datetime.fromisoformat(created_on_str)

            return distancia_float, created_on_dt

        except json.JSONDecodeError as e:
             print(f"  [Process] Erro ao decodificar JSON: {e}. Payload: {payload_str}")
             return None
        except (KeyError, ValueError, TypeError) as e:
             print(f"  [Process] Erro no conteúdo/formato do JSON: {e}. Payload: {payload_str}")
             return None
        except Exception as e:
            print(f"  [Process] Erro inesperado ao processar mensagem: {e}. Payload: {payload_str}")
            return None

    def connect(self) -> bool:
        """
        Tenta iniciar a conexão assíncrona com o broker MQTT.
        O sucesso ou falha real da conexão será indicado pelo callback _on_connect.
        """
        if self.is_connected:
             print("[MQTT Listener] Aviso: Já está conectado.")
             return True

        try:
            print(f"[MQTT Listener] Tentando conectar ao Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            # connect() é assíncrono.
            # Use o keepalive configurado (180s no último teste, pode voltar para 60s se preferir)
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=180)
            print(f"[MQTT Listener] Comando connect enviado (keepalive={self.client._keepalive}s). Aguardando callback _on_connect...")
            return True # Indica que a tentativa foi iniciada sem erro imediato
        except ssl.SSLError as e:
             print(f"[MQTT Listener] ERRO SSL ao tentar conectar: {e}")
             print(" -> Verifique configuração TLS, certificados CA no sistema, compatibilidade.")
             return False
        except OSError as e:
             print(f"[MQTT Listener] ERRO DE REDE/OS ao tentar conectar: {e}")
             print(" -> Verifique conectividade, DNS, firewall, endereço/porta do broker.")
             return False
        except Exception as e:
            print(f"[MQTT Listener] ERRO INESPERADO ao iniciar conexão: {e}")
            return False

    def start_listening(self):
        """Inicia o loop de rede principal para escutar mensagens (bloqueante)."""
        if not self.is_connected:
             print("[MQTT Listener] ERRO: Não pode iniciar loop de escuta - conexão não estabelecida.")
             print("[MQTT Listener] Verifique os logs anteriores para o motivo da falha na conexão.")
             return

        print("[MQTT Listener] Iniciando loop de escuta MQTT (blocking - use Ctrl+C para sair)...")
        try:
            # loop_forever() processa I/O de rede, callbacks e lida com reconexões (se não for erro fatal)
            self.client.loop_forever()
        except KeyboardInterrupt:
             print("\n[MQTT Listener] KeyboardInterrupt recebido no loop_forever.")
        except Exception as e:
             # Captura exceções que podem ocorrer *dentro* do loop do Paho
             # como o 'bad char in struct format' que vimos antes
             print(f"[MQTT Listener] ERRO CRÍTICO dentro do loop_forever Paho: {e}")
             # Adiciona um traceback para ajudar a diagnosticar onde no Paho o erro ocorreu
             import traceback
             traceback.print_exc()
             self.disconnect() # Tenta desconectar em caso de erro inesperado no loop
        finally:
            print("[MQTT Listener] Saindo/Terminando loop_forever.")

    def disconnect(self):
        """Desconecta o cliente MQTT de forma limpa."""
        if self.client:
            print("[MQTT Listener] Solicitando desconexão do cliente MQTT...")
            self.client.disconnect() # Solicita desconexão limpa
            print("[MQTT Listener] Comando de desconexão enviado.")
        else:
            print("[MQTT Listener] Cliente não inicializado, não há o que desconectar.")
        self.is_connected = False

# --- Fim da Classe MQTTListener ---