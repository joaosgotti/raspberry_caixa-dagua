#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_listener.py

import sys
import time
import config # Importa config para validação inicial (MQTT e DB check) e acesso às vars

# --- Dependências Externas ---
# Verificar importações e instalar se necessário
try:
    from db_handler import DatabaseHandler
    from mqtt_listener_logic import MQTTListener
    import psycopg2 # Necessário para DatabaseHandler
    import paho.mqtt.client # Para MQTTListener
except ImportError as e:
     missing_module = str(e).split("'")[-2] # Tenta pegar o nome do módulo
     print(f"Erro CRÍTICO: Dependência '{missing_module}' não encontrada.")
     print("Certifique-se de ter instalado todas as dependências:")
     print("pip install paho-mqtt psycopg2-binary python-dotenv")
     sys.exit(1)

def main():
    """Função principal para configurar e iniciar o listener MQTT e o handler do DB."""
    print("--- Iniciando Serviço MQTT Listener (com Banco de Dados) ---")

    # 1. Validação de Configuração Essencial
    # A validação MQTT ocorre no import de config.py
    print("[Main Listener] Verificando configuração do Banco de Dados...")
    if not config.check_db_config(): # Função de config.py que verifica vars DB_
        # Mensagem de erro específica já é impressa por check_db_config()
        print("[Main Listener] ERRO CRÍTICO: Configuração do Banco de Dados inválida ou ausente no .env. Encerrando.")
        sys.exit(1)
    else:
        print("[Main Listener] Configuração do Banco de Dados OK.")

    # 2. Inicializar Componentes
    db_handler_instance = None
    listener = None
    initialization_ok = False

    # Inicializa o Database Handler
    try:
        print("[Main Listener] Inicializando Database Handler...")
        db_handler_instance = DatabaseHandler()
        print("[Main Listener] Database Handler inicializado.")
    except Exception as db_init_err:
        print(f"[Main Listener] Erro CRÍTICO ao inicializar Database Handler: {db_init_err}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Inicializa o Listener MQTT, passando a instância do DB Handler
    try:
        print("[Main Listener] Inicializando MQTT Listener...")
        listener = MQTTListener(db_handler=db_handler_instance) # Passa a instância criada
        initialization_ok = True
        print("[Main Listener] MQTT Listener inicializado.")
    except Exception as mqtt_init_err:
         print(f"[Main Listener] Erro CRÍTICO durante a inicialização do MQTT Listener: {mqtt_init_err}")
         import traceback
         traceback.print_exc()
         # Limpeza: Se o DB Handler foi criado mas o MQTT falhou, não há muito o que fazer aqui.
         sys.exit(1)

    # 3. Conectar ao MQTT, Iniciar Loop de Rede e Esperar/Escutar
    if initialization_ok and listener:
        print("[Main Listener] Tentando iniciar conexão MQTT...")
        connection_attempted = listener.connect() # Tenta iniciar a conexão (assíncrono)

        if connection_attempted:
            # INICIA O LOOP DE REDE EM BACKGROUND para processar a conexão
            print("[Main Listener] Iniciando loop de rede Paho em background (loop_start)...")
            listener.client.loop_start()

            print("[Main Listener] Aguardando confirmação de conexão via callback (_on_connect)...")
            # Tempo para a conexão ser estabelecida e o callback ser chamado
            time.sleep(7) # 7 segundos (ajuste se necessário)

            # Verifica se o callback _on_connect confirmou a conexão
            if listener.is_connected:
                 print("[Main Listener] SUCESSO: Conexão MQTT confirmada pelo callback!")
                 print("[Main Listener] Iniciando loop principal de escuta bloqueante (loop_forever)...")
                 try:
                     # Chama a função que contém o loop_forever()
                     listener.start_listening()
                 except KeyboardInterrupt:
                     print("\n[Main Listener] Interrupção pelo usuário (Ctrl+C) recebida no loop principal.")
                 except Exception as loop_err:
                     # Captura erros inesperados que podem ocorrer durante o loop_forever
                     print(f"\n[Main Listener] ERRO INESPERADO durante a execução do loop principal: {loop_err}")
                     import traceback
                     traceback.print_exc()
                 finally:
                     print("[Main Listener] Saindo do loop principal (start_listening)...")
                     # Garante limpeza final
                     print("[Main Listener] Parando loop de rede Paho (loop_stop)...")
                     listener.client.loop_stop() # PARA O LOOP iniciado por loop_start ou usado por loop_forever
                     listener.disconnect() # Solicita desconexão MQTT limpa
            else:
                 # Se após esperar, a conexão não foi confirmada...
                 print("[Main Listener] FALHA: Conexão MQTT NÃO confirmada após o tempo de espera.")
                 print("[Main Listener] -> Verifique os logs (especialmente [MQTT PAHO LOG]) para erros.")
                 print("[Main Listener] -> Verifique credenciais no .env, status do broker, firewall.")
                 # Parar o loop de rede que iniciamos
                 print("[Main Listener] Parando loop de rede Paho (loop_stop) após falha na confirmação...")
                 listener.client.loop_stop()
                 listener.disconnect() # Tenta limpar o cliente

        else:
            # Se listener.connect() retornou False imediatamente
            print("[Main Listener] FALHA: Erro imediato ao tentar iniciar a conexão MQTT (ver logs do listener).")
            if listener:
                 listener.disconnect() # Tenta limpar se o objeto listener foi criado

    else:
         # Se a inicialização dos componentes falhou (já logado acima)
         print("[Main Listener] ERRO: Falha na inicialização dos componentes. Não foi possível iniciar.")


    print("\n--- Serviço MQTT Listener Finalizado ---")

# Bloco padrão para execução do script
if __name__ == "__main__":
    main() # Chama a função principal