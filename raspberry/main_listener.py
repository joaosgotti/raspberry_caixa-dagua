# main_listener.py
# -*- coding: utf-8 -*-

import sys
import time
import config # Importa config para validação MQTT (feita no import) e acesso às vars

# --- Dependências Externas ---
# Verificar importações e instalar se necessário
try:
    # Remova/Comente a linha abaixo se NÃO for usar o DB
    from db_handler import DatabaseHandler
    from mqtt_listener_logic import MQTTListener
    # Remova/Comente a linha abaixo se NÃO for usar o DB
    import psycopg2 # Necessário para type hint em DatabaseHandler
    import paho.mqtt.client # Para MQTTListener
except ImportError as e:
     missing_module = str(e).split("'")[-2] # Tenta pegar o nome do módulo
     print(f"Erro CRÍTICO: Dependência '{missing_module}' não encontrada.")
     # Ajuste a mensagem se não estiver usando DB
     print("Verifique se instalou com: pip install paho-mqtt psycopg2-binary python-dotenv")
     # print("Verifique se instalou com: pip install paho-mqtt python-dotenv") # Se sem DB
     sys.exit(1)


def main():
    """Função principal para configurar e iniciar o listener MQTT."""
    print("--- Iniciando Serviço MQTT Listener ---")

    # 1. Validação de Configuração Essencial
    # A validação MQTT ocorre no import de config.py
    # A validação DB é feita abaixo, apenas se formos usar o DB Handler

    # 2. Inicializar Componentes
    db_handler_instance = None # Começa como None
    listener = None
    initialization_ok = False

    # --- Bloco para Inicializar DB Handler (Opcional) ---
    # Descomente este bloco se quiser usar o banco de dados
    # print("[Main Listener] Verificando configuração do Banco de Dados...")
    # if config.check_db_config(): # Verifica se as variáveis DB existem no .env
    #     try:
    #         print("[Main Listener] Inicializando Database Handler...")
    #         db_handler_instance = DatabaseHandler()
    #         print("[Main Listener] Database Handler inicializado.")
    #     except Exception as db_init_err:
    #         print(f"[Main Listener] Erro CRÍTICO ao inicializar Database Handler: {db_init_err}")
    #         sys.exit(1)
    # else:
    #     print("[Main Listener] ERRO CRÍTICO: Configuração do Banco de Dados ausente no .env. Encerrando.")
    #     sys.exit(1)
    # --- Fim do Bloco DB Handler ---

    # Se não descomentou o bloco acima, db_handler_instance permanecerá None (Modo Teste sem DB)
    if db_handler_instance is None:
         print("[Main Listener] *** Rodando em MODO TESTE SEM BANCO DE DADOS ***")

    # Inicializa o Listener MQTT, passando o db_handler (que pode ser None)
    try:
        print("[Main Listener] Inicializando MQTT Listener...")
        # Passa a instância do DB Handler (ou None) para o Listener
        listener = MQTTListener(db_handler=db_handler_instance)
        initialization_ok = True
        print("[Main Listener] MQTT Listener inicializado.")
    except Exception as mqtt_init_err:
         print(f"[Main Listener] Erro CRÍTICO durante a inicialização do MQTT Listener: {mqtt_init_err}")
         sys.exit(1)

    # 3. Conectar, Iniciar Loop de Rede e Esperar/Escutar
    if initialization_ok and listener:
        print("[Main Listener] Tentando iniciar conexão MQTT...")
        connection_attempted = listener.connect() # Tenta iniciar a conexão (assíncrono)

        if connection_attempted:
            # --- PONTO CRUCIAL: INICIAR O LOOP DE REDE ---
            print("[Main Listener] Iniciando loop de rede Paho em background (loop_start)...")
            listener.client.loop_start() # <--- INICIA O PROCESSAMENTO DE REDE EM BACKGROUND
            # ----------------------------------------------

            print("[Main Listener] Aguardando confirmação de conexão via callback (_on_connect)...")
            # Dê tempo suficiente para o loop em background conectar e o callback ser chamado
            # Aumentar se a rede/broker for lento
            time.sleep(7) # Aumentei para 7 segundos para dar mais margem

            # Verifica se o callback _on_connect atualizou o status
            if listener.is_connected:
                 print("[Main Listener] SUCESSO: Conexão MQTT confirmada pelo callback!")
                 print("[Main Listener] Iniciando loop principal de escuta bloqueante (loop_forever)...")
                 try:
                     # Agora chama start_listening, que internamente usa loop_forever()
                     # O loop_forever vai assumir o controle do processamento de rede.
                     listener.start_listening()
                 except KeyboardInterrupt:
                     print("\n[Main Listener] Interrupção pelo usuário (Ctrl+C) recebida no loop principal.")
                 except Exception as loop_err:
                     print(f"\n[Main Listener] ERRO INESPERADO durante a execução do loop principal: {loop_err}")
                 finally:
                     print("[Main Listener] Saindo do loop principal (start_listening)...")
                     # Garante que o loop em background (se ainda ativo) seja parado e desconecte
                     print("[Main Listener] Parando loop de rede Paho (loop_stop)...")
                     listener.client.loop_stop() # PARA O LOOP QUE INICIAMOS (ou que loop_forever usou)
                     listener.disconnect() # Solicita desconexão limpa
            else:
                 # Se após esperar, a conexão não foi confirmada...
                 print("[Main Listener] FALHA: Conexão MQTT NÃO confirmada após o tempo de espera.")
                 print("[Main Listener] -> Verifique os logs (especialmente os [MQTT PAHO LOG]) para erros de rede, TLS ou autenticação.")
                 print("[Main Listener] -> Verifique credenciais no .env, status do broker HiveMQ, firewall.")
                 # Parar o loop que iniciamos, mesmo em caso de falha
                 print("[Main Listener] Parando loop de rede Paho (loop_stop) após falha na confirmação...")
                 listener.client.loop_stop() # PARA O LOOP QUE INICIAMOS
                 listener.disconnect() # Tenta limpar o cliente

        else:
            # Se listener.connect() retornou False imediatamente (raro, mas possível)
            print("[Main Listener] FALHA: Erro imediato ao tentar iniciar a conexão MQTT (ver logs anteriores).")
            # Não precisamos parar o loop aqui pois ele nem foi iniciado
            if listener:
                 listener.disconnect() # Tenta limpar o cliente mesmo assim

    else:
         print("[Main Listener] ERRO: Falha na inicialização dos componentes. Não foi possível iniciar a conexão.")


    print("\n--- Serviço MQTT Listener Finalizado ---")

if __name__ == "__main__":
    # Verifica se o script está sendo executado diretamente
    main() # Chama a função principal