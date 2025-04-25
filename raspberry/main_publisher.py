#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_publisher.py
# Script principal para ler o sensor HC-SR04 e publicar via MQTT.
# Utiliza os módulos sensor_reader e mqtt_publisher.

import time
import json
from datetime import datetime, timezone
import sys
import os
import RPi.GPIO # Importa para a limpeza final

# Módulos locais do projeto
try:
    import config         # Carrega configurações do .env
    import sensor_reader  # Módulo para ler o sensor real
    from mqtt_publisher import MQTTPublisher # Classe para publicar MQTT
except ImportError as e:
    print(f"Erro ao importar módulos necessários: {e}")
    print("Verifique se os arquivos config.py, sensor_reader.py e mqtt_publisher.py estão no mesmo diretório.")
    sys.exit(1)
except Exception as e:
    print(f"Erro inesperado durante a importação: {e}")
    sys.exit(1)

def run_publisher_with_sensor():
    """Função principal para executar o ciclo de leitura do sensor e publicação via MQTT."""
    print("--- Iniciando Aplicação Publisher (com Sensor Real) ---")

    # 1. Cria instância do Publicador MQTT
    print("Inicializando MQTT Publisher...")
    publisher = MQTTPublisher()

    # 2. Tenta conectar ao Broker MQTT
    if not publisher.connect():
        print("Falha ao iniciar a conexão com o broker MQTT. Encerrando.")
        try:
            sensor_reader.cleanup_gpio()
        except Exception as gpio_err:
             print(f"Erro durante a limpeza do GPIO após falha no MQTT: {gpio_err}")
        return # Sai da função

    # 3. Pausa para aguardar a conexão inicial
    print("Aguardando alguns segundos para a conexão inicial com o broker MQTT...")
    time.sleep(5) # Ajuste este valor conforme a necessidade da sua rede

    # Verifica se a conexão foi estabelecida após a pausa
    if not publisher.is_connected:
         print("Não foi possível confirmar a conexão MQTT após a espera. Encerrando.")
         publisher.disconnect()
         sensor_reader.cleanup_gpio() # Garante a limpeza do GPIO
         return # Sai da função

    # 4. Loop Principal de Leitura e Publicação
    print("\n--- Iniciando Loop de Leitura e Publicação (Ctrl+C para parar) ---")
    try:
        while True:
            # Lê a distância do sensor real
            distancia_lida = sensor_reader.read_distance()

            if distancia_lida is not None:
                # Validação básica da leitura do sensor
                if 5 < distancia_lida < 400: # Exemplo de faixa válida (ajuste conforme seu sensor e ambiente)
                    print(f"Leitura do sensor: {distancia_lida:.1f} cm (Válida)")
                    # Cria o payload (dados a serem enviados) como um dicionário Python
                    payload_dict = {
                        "distancia": round(distancia_lida), # Arredonda a distância para um número inteiro
                        "created_on": datetime.now(timezone.utc).isoformat() # Timestamp no formato ISO 8601 com UTC
                    }
                    # Publica os dados formatados como JSON usando a instância do publisher
                    publisher.publish_data(payload_dict)
                else:
                    print(f"Leitura do sensor: {distancia_lida:.1f} cm (Fora da faixa esperada, ignorando)")
            else:
                # O módulo sensor_reader já imprime mensagens de erro/timeout internamente
                print("[Publisher Main] Falha ao ler o sensor (timeout ou erro). Pulando a publicação.")

            # Aguarda o intervalo configurado antes da próxima leitura/publicação
            print(f"Aguardando {config.PUBLISH_INTERVAL_SECONDS} segundos para a próxima leitura...")
            time.sleep(config.PUBLISH_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nInterrupção pelo usuário (Ctrl+C) recebida. Encerrando o publisher...")
    except Exception as e:
        print(f"\nErro inesperado no loop principal do publisher: {e}")
        import traceback
        traceback.print_exc() # Imprime informações detalhadas sobre o erro
    finally:
        # Bloco finally garante que a limpeza será executada mesmo em caso de erro ou interrupção
        print("Encerrando a aplicação publisher...")
        # Desconecta do broker MQTT se o publisher foi inicializado
        if publisher:
            publisher.disconnect()
        # Limpa os pinos GPIO utilizados pelo sensor
        print("Limpando os pinos GPIO...")
        sensor_reader.cleanup_gpio()
        print("Aplicação publisher finalizada.")

# Ponto de entrada do script
if __name__ == "__main__":
    # Verifica se o script está sendo executado diretamente
    # --- IMPORTANTE: Permissões GPIO ---
    if os.geteuid() != 0:
         print("AVISO: Este script pode precisar de permissões de root (sudo) para acessar os pinos GPIO.")
         # Em alguns sistemas, pode ser necessário executar com 'sudo python main_publisher.py'
         # para que o acesso ao GPIO seja permitido.

    run_publisher_with_sensor() # Chama a função principal de execução do publisher