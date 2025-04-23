# main_listener.py
import sys
import time
import config # Apenas para checar config inicial

# --- Dependências Externas ---
# Verificar importações e instalar se necessário
try:
    from db_handler import DatabaseHandler
    from mqtt_listener_logic import MQTTListener
    import psycopg2 # Para DatabaseHandler
    import paho.mqtt.client # Para MQTTListener
except ImportError as e:
     missing_module = str(e).split("'")[-2] # Tenta pegar o nome do módulo
     print(f"Erro: Dependência '{missing_module}' não encontrada.")
     print("Verifique se instalou com: pip install paho-mqtt psycopg2-binary python-dotenv")
     sys.exit(1)


def main():
    """Função principal para configurar e iniciar o listener."""
    print("--- Iniciando Serviço MQTT Listener ---")

    # 1. Verificar Configurações Essenciais
    if not config.check_db_config():
        print("Encerrando devido à falta de configuração do banco de dados no .env.")
        sys.exit(1)
    # A configuração MQTT já é validada no config.py globalmente

    # 2. Inicializar Componentes
    db_handler = None
    listener = None
    initialization_ok = False
    try:
        db_handler = DatabaseHandler()
        listener = MQTTListener(db_handler) # Passa o handler do DB para o listener
        initialization_ok = True
    except Exception as e:
         print(f"Erro crítico durante a inicialização dos handlers: {e}")
         sys.exit(1)

    # 3. Conectar e Iniciar o Listener
    if initialization_ok and listener:
        connection_attempted = listener.connect()

        if connection_attempted:
            print("[Main Listener] Conexão MQTT iniciada. Aguardando confirmação via callback...")
            # Espera um pouco para dar chance ao callback _on_connect
            # antes de entrar no loop bloqueante.
            time.sleep(5) # Ajuste conforme a velocidade da sua rede/broker

            if listener.is_connected:
                 print("[Main Listener] Conexão confirmada. Iniciando loop.")
                 try:
                     # Inicia o loop bloqueante que escuta as mensagens
                     listener.start_listening()
                 except KeyboardInterrupt:
                     print("\n[Main Listener] Interrupção pelo usuário recebida no loop.")
                 except Exception as e:
                     print(f"\n[Main Listener] Erro inesperado durante a execução do loop: {e}")
                 finally:
                     print("[Main Listener] Saindo do loop de escuta...")
            else:
                 print("[Main Listener] Falha ao confirmar conexão MQTT após tentativa inicial.")
                 print("[Main Listener] Verifique os logs do Listener, rede, credenciais e status do Broker.")
                 # Tentar desconectar mesmo assim para limpar recursos
                 listener.disconnect()

        else:
            print("[Main Listener] Falha ao iniciar a tentativa de conexão MQTT. Verifique logs.")
            # Listener pode não ter sido totalmente configurado se connect() falhou cedo
            if listener:
                 listener.disconnect() # Tenta limpar o cliente MQTT se existir

    print("\n--- Serviço MQTT Listener Finalizado ---")

if __name__ == "__main__":
    main()