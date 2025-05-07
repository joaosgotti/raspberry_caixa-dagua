#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_listener.py
# Script principal para iniciar o listener MQTT e o handler do banco de dados.
# Utiliza os módulos mqtt_listener e database_handler.

import time
import sys

# Módulos locais do projeto
try:
    import config # Apenas para verificar a configuração do DB
    from mqtt_listener import MQTTListener
    from database_handler import DatabaseHandler
except ImportError as e:
    print(f"Erro ao importar módulos necessários: {e}")
    print("Verifique se os arquivos config.py, mqtt_listener.py e database_handler.py estão no mesmo diretório.")
    sys.exit(1)
except Exception as e:
    print(f"Erro inesperado durante a importação: {e}")
    sys.exit(1)

def run_listener_with_db():
    """Função principal para executar o listener MQTT e persistir os dados no banco de dados."""
    print("--- Iniciando Aplicação Listener (com Banco de Dados) ---")

    # 1. Verifica se a configuração do banco de dados está presente e completa no arquivo .env
    if not config.check_db_config_present():
        sys.exit("Configuração do banco de dados ausente ou incompleta no .env. Encerrando o listener.")

    # 2. Cria uma instância do DatabaseHandler para interagir com o banco de dados
    print("Inicializando Database Handler...")
    try:
        db_handler = DatabaseHandler()
    except Exception as e:
        print(f"Erro CRÍTICO ao inicializar o Database Handler: {e}")
        sys.exit(1)

    # 3. Cria uma instância do MQTTListener, passando a instância do DatabaseHandler para persistir os dados recebidos
    print("Inicializando MQTT Listener...")
    try:
        listener = MQTTListener(db_handler=db_handler)
    except Exception as e:
        print(f"Erro CRÍTICO ao inicializar o MQTT Listener: {e}")
        sys.exit(1)

    # 4. Tenta conectar ao broker MQTT
    if not listener.connect():
        print("Falha ao iniciar a conexão inicial com o broker MQTT. Encerrando o listener.")
        return # Sai da função

    # 5. Inicia o loop principal de escuta do MQTT (esta função é bloqueante)
    # O Paho MQTT lida com a manutenção da conexão e a recepção de mensagens dentro deste loop.
    print("[Listener] Iniciando o loop principal de escuta (loop_forever)...")
    try:
        listener.start_listening() # Esta chamada bloqueará a thread principal até que ocorra uma interrupção
    except Exception as e:
        # Captura erros que possam ocorrer fora dos callbacks do Paho MQTT
        print(f"Erro fatal não capturado durante o loop principal do listener: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Bloco finally garante que a desconexão do MQTT ocorra ao sair do loop (por Ctrl+C ou erro)
        print("Encerrando a aplicação listener...")
        if listener: # Verifica se a instância do listener foi criada com sucesso
            listener.disconnect()
        print("Aplicação listener finalizada.")

# Ponto de entrada do script
if __name__ == "__main__":
    # Verifica se o script está sendo executado diretamente
    run_listener_with_db() # Chama a função principal de execução do listener