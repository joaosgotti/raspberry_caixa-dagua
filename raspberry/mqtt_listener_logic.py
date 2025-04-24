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
    Inclui logging detalhado para diagnóstico de conexão.
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
        # Filtra logs muito verbosos (INFO, DEBUG) se necessário
        # levels: MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR, MQTT_LOG_DEBUG
        if level == mqtt.MQTT_LOG_WARNING or level == mqtt.MQTT_LOG_ERR:
             print(f"[MQTT PAHO LOG | Lvl:{level} | WARN/ERR] {buf}")
        elif level == mqtt.MQTT_LOG_DEBUG:
             # Descomente a linha abaixo para ver ABSOLUTAMENTE TUDO (muito verboso!)
             # print(f"[MQTT PAHO LOG | Lvl:{level} | DEBUG] {buf}")
             pass
        else:
             # Imprime INFO e NOTICE
             print(f"[MQTT PAHO LOG | Lvl:{level} | INFO/NOTICE] {buf}")


    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback executado quando a conexão MQTT é estabelecida ou falha."""
        # DEBUG: Imprime o código de retorno sempre
        print(f"[MQTT Listener] Callback _on_connect chamado com código de retorno (rc): {rc}")

        if rc == 0:
            self.is_connected = True
            print(f"[MQTT Listener] CONECTADO com sucesso ao Broker MQTT!")
            try:
                print(f"[MQTT Listener] Inscrevendo-se no tópico: '{config.MQTT_TOPIC}' com QoS 1...")
                result, mid = client.subscribe(config.MQTT_TOPIC, qos=1)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    print(f"[MQTT Listener] >> Inscrito com sucesso (MID: {mid})")
                else:
                    # Usar função da Paho para descrever o erro de subscribe
                    print(f"[MQTT Listener] ERRO ao inscrever no tópico! Código Paho: {result} - {mqtt.error_string(result)}")
            except Exception as e:
                print(f"[MQTT Listener] ERRO EXCEPCIONAL durante a inscrição no tópico '{config.MQTT_TOPIC}': {e}")
        else:
            self.is_connected = False
            # Imprime o erro específico baseado no código rc usando função da Paho
            error_message = mqtt.connack_string(rc)
            print(f"[MQTT Listener] FALHA NA CONEXÃO com Broker MQTT (Código: {rc}) - {error_message}")
            print("[MQTT Listener] -> VERIFIQUE: Endereço/Porta do Broker, Credenciais (usuário/senha), Configuração TLS, Rede/Firewall, Status do Broker.")
            # Considerar parar tentativas se for erro de autenticação claro
            if rc in [mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD, mqtt.CONNACK_REFUSED_NOT_AUTHORIZED]:
                 print("[MQTT Listener] *** Erro crítico de autenticação/autorização. Verifique as credenciais IMEDIATAMENTE. ***")


    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback executado quando a conexão MQTT é perdida."""
         # DEBUG: Imprime o código de retorno sempre
        print(f"[MQTT Listener] Callback _on_disconnect chamado com código de retorno (rc): {rc}")
        was_connected = self.is_connected # Guarda o estado anterior
        self.is_connected = False
        if rc == 0:
             print("[MQTT Listener] Desconexão limpa iniciada pelo cliente ou broker.")
        else:
            # Tenta obter a descrição do erro
            reason = mqtt.error_string(rc) if rc in mqtt.error_string_map else f"Código de erro Paho desconhecido: {rc}"
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
                # print("  [MQTT Listener] Tentando interação com o Banco de Dados...") # Log opcional
                connection = None
                try:
                    connection = self.db_handler.connect()
                    if connection:
                        success = self.db_handler.insert_reading(connection, distancia, created_on_dt)
                        # db_handler já imprime sucesso ou falha na inserção
                        if not success:
                             print("  [MQTT Listener] Falha ao inserir no DB (ver logs do DB Handler).")
                    else:
                        print("  [MQTT Listener] Falha ao conectar ao DB nesta tentativa.")
                except Exception as db_err:
                     print(f"  [MQTT Listener] ERRO durante interação com DB: {db_err}")
                finally:
                    if connection:
                        self.db_handler.close(connection)
            # else: # Modo teste sem DB, não precisa imprimir nada aqui
            #     pass
            # --- Fim da Interação com o Banco de Dados ---
        else:
            print(f"  [MQTT Listener] Falha ao processar JSON da mensagem. Payload: {payload_str}")

    # --- Métodos de Controle do Cliente ---

    def _configure_client(self):
        """Configura autenticação, TLS e todos os callbacks para o cliente MQTT."""
        print("[MQTT Listener] Configurando cliente Paho...")
        try:
            # 1. Autenticação
            # === OPÇÃO 1: Ler do config.py (Normal) ===
            if config.MQTT_USER and config.MQTT_PASSWORD:
                self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
                print("[MQTT Listener] Usando Usuário/Senha do config.py.")
            elif config.MQTT_USER:
                 print("[MQTT Listener] Usando apenas Usuário do config.py (sem senha).")
                 self.client.username_pw_set(config.MQTT_USER)
            else:
                print("[MQTT Listener] Conectando sem usuário/senha MQTT (config não definido).")

            # === OPÇÃO 2: Credenciais Hardcoded (APENAS PARA TESTE, LEMBRE-SE DE REMOVER!) ===
            # print("[MQTT Listener] ATENÇÃO: Usando credenciais HARDCODED para teste!")
            # self.client.username_pw_set("joaosgotti", "sS123412") # <<< DESCOMENTE APENAS PARA TESTAR

            # 2. Configuração TLS (se porta for 8883)
            if config.MQTT_PORT == 8883:
                print("[MQTT Listener] Configurando TLS (porta 8883 detectada)...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[MQTT Listener] TLS v1.2 configurado.")

                # === OPÇÃO 3: Bypass Validação Certificado (INSEGURO - APENAS PARA TESTE!) ===
                # print("[MQTT Listener] ATENÇÃO: Habilitando tls_insecure_set(True) para teste!")
                # self.client.tls_insecure_set(True) # DESCOMENTE APENAS PARA TESTAR PROBLEMAS DE CERTIFICADO
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

            # Validação opcional de limites
            # if not (0 < distancia_float < 1000): # Exemplo
            #     print(f"  [Process] Aviso: Distancia ({distancia_float}) fora do limite esperado.")

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
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
            print("[MQTT Listener] Comando connect enviado. Aguardando callback _on_connect...")
            # É importante que o loop de rede seja iniciado depois para processar o CONNACK
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
        # Verifica se a conexão foi estabelecida antes de bloquear
        # (Nota: o main_listener.py já faz essa checagem após um sleep)
        if not self.is_connected:
             print("[MQTT Listener] ERRO: Não pode iniciar loop de escuta - conexão não estabelecida.")
             print("[MQTT Listener] Verifique os logs anteriores para o motivo da falha na conexão.")
             return

        print("[MQTT Listener] Iniciando loop de escuta MQTT (bloqueante - use Ctrl+C para sair)...")
        try:
            # loop_forever() processa I/O de rede, callbacks e lida com reconexões (se não for erro fatal)
            self.client.loop_forever()
        except KeyboardInterrupt:
             print("\n[MQTT Listener] KeyboardInterrupt recebido no loop_forever.")
             # A desconexão será tratada no bloco finally do main_listener.py
        except Exception as e:
             print(f"[MQTT Listener] ERRO CRÍTICO dentro do loop_forever Paho: {e}")
             self.disconnect() # Tenta desconectar em caso de erro inesperado no loop
        finally:
            print("[MQTT Listener] Saindo/Terminando loop_forever.")

    def disconnect(self):
        """Desconecta o cliente MQTT de forma limpa."""
        if self.client:
            # Verifica se o cliente está conectado antes de tentar desconectar
            # (A biblioteca Paho pode ter sua própria flag interna)
            print("[MQTT Listener] Solicitando desconexão do cliente MQTT...")
            self.client.disconnect() # Solicita desconexão limpa
            # self.client.loop_stop() # Necessário se estivesse usando loop_start()
            print("[MQTT Listener] Comando de desconexão enviado.")
        else:
            print("[MQTT Listener] Cliente não inicializado, não há o que desconectar.")
        # Garante que o estado interno seja atualizado
        self.is_connected = False

# --- Fim da Classe MQTTListener ---