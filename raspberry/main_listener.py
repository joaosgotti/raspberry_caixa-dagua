#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_listener.py (Adaptado para Listener Simplificado)

import sys
import time
import config

# --- Dependências ---
try:
    # Mantenha comentado se não for usar DB
    # from db_handler import DatabaseHandler
    from mqtt_listener_logic import MQTTListener # Importa a versão SIMPLIFICADA agora
    # Mantenha comentado se não for usar DB
    # import psycopg2
    import paho.mqtt.client as mqtt # Para acesso ao client dentro do listener
except ImportError as e:
     missing_module = str(e).split("'")[-2]
     print(f"Erro CRÍTICO: Dependência '{missing_module}' não encontrada.")
     # Ajuste a mensagem conforme o uso ou não do DB
     # print("Verifique: pip install paho-mqtt psycopg2-binary python-dotenv")
     print("Verifique: pip install paho-mqtt python-dotenv")
     sys.exit(1)

def main():
    """Função principal - versão simplificada."""
    print("--- Iniciando Serviço MQTT Listener (VERSÃO SIMPLIFICADA) ---")

    # 1. Configuração e Inicialização DB (Mantido COMENTADO para teste)
    db_handler_instance = None
    # print("[Main Listener] Verificando configuração do Banco de Dados...")
    # if config.check_db_config():
    #     try:
    #         print("[Main Listener] Inicializando Database Handler...")
    #         db_handler_instance = DatabaseHandler()
    #         print("[Main Listener] Database Handler inicializado.")
    #     except Exception as db_init_err:
    #         print(f"[Main Listener] Erro CRÍTICO ao inicializar DB Handler: {db_init_err}")
    #         sys.exit(1)
    # else:
    #     print("[Main Listener] ERRO CRÍTICO: Configuração do Banco de Dados ausente. Encerrando.")
    #     sys.exit(1)

    if db_handler_instance is None:
         print("[Main Listener] *** Rodando em MODO TESTE SEM BANCO DE DADOS ***")

    # 2. Inicializar Listener MQTT Simplificado
    listener = None
    initialization_ok = False
    try:
        print("[Main Listener] Inicializando MQTT Listener (simplificado)...")
        listener = MQTTListener(db_handler=db_handler_instance)
        initialization_ok = True
        print("[Main Listener] MQTT Listener (simplificado) inicializado.")
    except Exception as mqtt_init_err:
         print(f"[Main Listener] Erro CRÍTICO na inicialização do MQTT Listener: {mqtt_init_err}")
         sys.exit(1)

    # 3. Conectar, Inscrever (APÓS CONECTAR!), e Escutar
    if initialization_ok and listener:
        print("[Main Listener] Tentando iniciar conexão MQTT...")
        connection_attempted = listener.connect()

        if connection_attempted:
            print("[Main Listener] Iniciando loop de rede Paho em background (loop_start)...")
            listener.client.loop_start() # ESSENCIAL para processar a conexão

            print("[Main Listener] Aguardando confirmação de conexão...")
            time.sleep(7) # Tempo para conectar

            if listener.is_connected:
                 print("[Main Listener] SUCESSO: Conexão MQTT confirmada!")

                 # --- INSCRIÇÃO INICIAL (APÓS CONFIRMAR CONEXÃO) ---
                 try:
                     topic = config.MQTT_TOPIC
                     qos = 1
                     print(f"[Main Listener] Inscrevendo no tópico inicial: '{topic}' QoS {qos}...")
                     result, mid = listener.client.subscribe(topic, qos)
                     if result == mqtt.MQTT_ERR_SUCCESS:
                         print(f"[Main Listener] Inscrito com sucesso (MID: {mid}).")
                     else:
                          print(f"[Main Listener] ERRO ao inscrever inicialmente! Código Paho: {result} - {mqtt.error_string(result)}")
                          # Decide se quer continuar mesmo sem inscrição inicial
                          # sys.exit(1) # Ou sair se a inscrição for crítica
                 except Exception as sub_err:
                      print(f"[Main Listener] ERRO EXCEPCIONAL na inscrição inicial: {sub_err}")
                      # sys.exit(1)
                 # --- FIM DA INSCRIÇÃO INICIAL ---

                 # Só continua para o loop principal se a inscrição inicial deu certo (ou se decidiu continuar mesmo com erro)
                 if result == mqtt.MQTT_ERR_SUCCESS: # Verifica se a inscrição deu certo
                    print("[Main Listener] Iniciando loop principal de escuta (loop_forever)...")
                    try:
                        listener.start_listening() # Chama a função com loop_forever
                    except KeyboardInterrupt:
                        print("\n[Main Listener] Interrupção pelo usuário (Ctrl+C).")
                    except Exception as loop_err:
                        print(f"\n[Main Listener] ERRO INESPERADO no loop principal: {loop_err}")
                    finally:
                        print("[Main Listener] Saindo do loop principal...")
                 else:
                      print("[Main Listener] Não foi possível inscrever no tópico inicial. Encerrando.")

                 # Limpeza final (executa após loop ou falha na inscrição)
                 print("[Main Listener] Parando loop de rede Paho (loop_stop)...")
                 listener.client.loop_stop()
                 listener.disconnect()

            else:
                 print("[Main Listener] FALHA: Conexão MQTT NÃO confirmada após espera.")
                 print("[Main Listener] -> Verifique logs, rede, credenciais, status do broker.")
                 print("[Main Listener] Parando loop de rede Paho (loop_stop)...")
                 listener.client.loop_stop()
                 listener.disconnect()
        else:
            print("[Main Listener] FALHA: Erro imediato ao tentar iniciar conexão.")
            if listener:
                 listener.disconnect()
    else:
         print("[Main Listener] ERRO: Falha na inicialização.")

    print("\n--- Serviço MQTT Listener Finalizado ---")

if __name__ == "__main__":
    main()