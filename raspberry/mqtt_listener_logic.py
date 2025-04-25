# mqtt_listener_logic.py (Versão Simplificada)
# -*- coding: utf-8 -*-

import ssl
import os
import json
from datetime import datetime
import time
from typing import Optional, Tuple, Any
import sys

import config

# Mantenha comentado se não for usar DB
# from db_handler import DatabaseHandler

try:
    import paho.mqtt.client as mqtt
except ImportError as e:
     print(f"Erro CRÍTICO: Dependência paho-mqtt não encontrada - {e}")
     print("Por favor, instale com: pip install paho-mqtt")
     sys.exit(1)


class MQTTListener:
    """
    Versão SIMPLIFICADA: Escuta mensagens MQTT, processa JSON.
    Sem logging Paho detalhado e sem re-inscrição explícita no on_connect.
    """

    def __init__(self, db_handler: Optional[Any] = None):
        # if db_handler is not None and 'DatabaseHandler' in globals() and not isinstance(db_handler, DatabaseHandler):
        #      raise TypeError("db_handler deve ser uma instância de DatabaseHandler")

        self.db_handler = db_handler
        self.client_id = f"mqtt_listener_simple_{os.getpid()}_{time.time():.0f}"
        print(f"[MQTT Listener] Usando Client ID: {self.client_id}")
        # Usar clean_session=False (padrão) tenta manter a sessão e inscrições no broker após desconexão
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311, clean_session=False)
        self.is_connected = False

        self._configure_client()

        print("[MQTT Listener] Instância criada (simplificada).")
        if self.db_handler is None:
            print("[MQTT Listener] *** MODO TESTE SEM BANCO DE DADOS ATIVADO ***")

    # --- Callbacks Paho MQTT (Simplificados) ---

    # REMOVIDO _on_log

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback executado quando a conexão MQTT é estabelecida ou falha."""
        print(f"[MQTT Listener] Callback _on_connect chamado com código de retorno (rc): {rc}")

        if rc == 0:
            self.is_connected = True
            print(f"[MQTT Listener] CONECTADO com sucesso ao Broker MQTT!")
            # NÃO fazemos subscribe aqui nesta versão simplificada. Faremos no main_listener após confirmar a conexão.
        else:
            self.is_connected = False
            error_message = mqtt.connack_string(rc) # Mantém a descrição útil
            print(f"[MQTT Listener] FALHA NA CONEXÃO com Broker MQTT (Código: {rc}) - {error_message}")
            # Simplesmente loga, a lógica de parada/reconexão está no loop principal/Paho

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback executado quando a conexão MQTT é perdida."""
        print(f"[MQTT Listener] Callback _on_disconnect chamado com código de retorno (rc): {rc}")
        self.is_connected = False # Garante que o estado seja atualizado
        if rc == 0:
             print("[MQTT Listener] Desconexão limpa.")
        else:
            # Usa a descrição do erro, mas sem lógica extra
            reason = mqtt.error_string(rc)
            print(f"[MQTT Listener] DESCONECTADO INESPERADAMENTE (Código: {rc}). Razão: {reason}")
            print("[MQTT Listener] -> Tentativa de reconexão automática pelo loop Paho (se aplicável)...")


    def _on_message(self, client, userdata, message: mqtt.MQTTMessage):
        """Callback executado quando uma mensagem MQTT é recebida."""
        try:
            payload_str = message.payload.decode('utf-8')
            print(f"\n[MQTT Listener] Mensagem recebida | Tópico: {message.topic} | QoS: {message.qos}")
        except UnicodeDecodeError as e:
            print(f"\n[MQTT Listener] ERRO ao decodificar payload | Tópico: {message.topic} | Erro: {e}")
            return

        processed_data = self._process_message(payload_str)

        if processed_data:
            distancia, created_on_dt = processed_data
            print(f"  Dados processados: Dist={distancia:.1f}, CreatedOn={created_on_dt.strftime('%Y-%m-%d %H:%M:%S%z')}")

            # Lógica do DB (permanece igual, só executa se db_handler existir)
            if self.db_handler:
                connection = None
                try:
                    connection = self.db_handler.connect()
                    if connection:
                        success = self.db_handler.insert_reading(connection, distancia, created_on_dt)
                        if not success:
                             print("  [MQTT Listener] Falha ao inserir no DB.")
                    else:
                        print("  [MQTT Listener] Falha ao conectar ao DB.")
                except Exception as db_err:
                     print(f"  [MQTT Listener] ERRO durante interação com DB: {db_err}")
                finally:
                    if connection:
                        self.db_handler.close(connection)
        else:
            print(f"  [MQTT Listener] Falha ao processar JSON. Payload: {payload_str}")

    # --- Métodos de Controle do Cliente ---

    def _configure_client(self):
        """Configura autenticação e TLS (SEM logging Paho detalhado)."""
        print("[MQTT Listener] Configurando cliente Paho (simplificado)...")
        try:
            # Autenticação
            if config.MQTT_USER and config.MQTT_PASSWORD:
                self.client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
                print("[MQTT Listener] Usando Usuário/Senha do config.py.")
            # (omitido caso de apenas usuário)
            else:
                print("[MQTT Listener] Conectando sem usuário/senha MQTT.")

            # TLS
            if config.MQTT_PORT == 8883:
                print("[MQTT Listener] Configurando TLS (porta 8883)...")
                self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
                print("[MQTT Listener] TLS v1.2 configurado.")
            else:
                print("[MQTT Listener] Conexão sem TLS.")

            # Callbacks Essenciais
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            # REMOVIDO self.client.on_log = self._on_log

            print("[MQTT Listener] Configuração do cliente Paho finalizada (simplificada).")

        except Exception as e:
            print(f"[MQTT Listener] ERRO CRÍTICO ao configurar cliente Paho MQTT: {e}")
            raise

    def _process_message(self, payload_str: str) -> Optional[Tuple[float, datetime]]:
        """Processa o payload JSON (sem alterações)."""
        try:
            dados = json.loads(payload_str)
            if not isinstance(dados, dict): raise ValueError("Payload não é dicionário.")
            if 'distancia' not in dados or 'created_on' not in dados: raise KeyError("Chaves ausentes.")

            distancia = dados['distancia']
            created_on_str = dados['created_on']
            distancia_float = float(distancia)
            created_on_dt = datetime.fromisoformat(created_on_str)
            return distancia_float, created_on_dt
        except Exception as e:
            print(f"  [Process] Erro ao processar mensagem: {e}. Payload: {payload_str}")
            return None

    def connect(self) -> bool:
        """Inicia a conexão assíncrona (sem alterações significativas)."""
        if self.is_connected:
             print("[MQTT Listener] Aviso: Já está conectado.")
             return True
        try:
            print(f"[MQTT Listener] Tentando conectar ao Broker: {config.MQTT_BROKER}:{config.MQTT_PORT}...")
            # Usar keepalive padrão de 60s ou o do .env se definido
            keepalive = int(os.getenv("MQTT_KEEPALIVE", 60))
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=keepalive)
            print(f"[MQTT Listener] Comando connect enviado (keepalive={keepalive}s). Aguardando callback...")
            return True
        except Exception as e:
            print(f"[MQTT Listener] ERRO INESPERADO ao iniciar conexão: {e}")
            return False

    def start_listening(self):
        """Inicia o loop bloqueante (sem alterações significativas)."""
        if not self.is_connected:
             print("[MQTT Listener] ERRO: Conexão não estabelecida antes de iniciar loop.")
             return
        print("[MQTT Listener] Iniciando loop de escuta MQTT (blocking)...")
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
             print("\n[MQTT Listener] KeyboardInterrupt recebido.")
        except Exception as e:
             print(f"[MQTT Listener] ERRO CRÍTICO dentro do loop_forever Paho: {e}")
             # Não temos mais o traceback aqui nesta versão simplificada
             self.disconnect()
        finally:
            print("[MQTT Listener] Saindo do loop_forever.")

    def disconnect(self):
        """Desconecta o cliente (sem alterações)."""
        if self.client:
            print("[MQTT Listener] Solicitando desconexão...")
            self.client.disconnect()
            print("[MQTT Listener] Comando de desconexão enviado.")
        else:
            print("[MQTT Listener] Cliente não inicializado.")
        self.is_connected = False