#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_publisher.py
# Script principal para ler a MEDIANA do sensor HC-SR04 e publicar via MQTT.
# Utiliza os módulos sensor_reader (versão com mediana) e mqtt_publisher.

import time
import json
from datetime import datetime, timezone
import sys
import os
# Removido: import RPi.GPIO (não é mais necessário aqui, sensor_reader gerencia)

# Módulos locais do projeto
try:
    import config         # Carrega configurações do .env
    import sensor_reader  # Módulo para ler o sensor (AGORA COM MEDIANA)
    from mqtt_publisher import MQTTPublisher # Classe para publicar MQTT
except ImportError as e:
    print(f"Erro ao importar módulos necessários: {e}")
    print("Verifique se os arquivos config.py, sensor_reader.py e mqtt_publisher.py estão no mesmo diretório.")
    sys.exit(1)
except Exception as e:
    print(f"Erro inesperado durante a importação: {e}")
    sys.exit(1)

def run_publisher_with_sensor():
    """Função principal para executar o ciclo de leitura da MEDIANA do sensor e publicação via MQTT."""
    print("--- Iniciando Aplicação Publisher (com Leitura de Mediana do Sensor) ---")
    publisher = None # Inicializa publisher como None para o finally

    # --- PASSO NOVO: Inicializar GPIO ---
    # É crucial chamar setup_gpio ANTES de qualquer tentativa de leitura
    print("Inicializando GPIO via sensor_reader...")
    if not sensor_reader.setup_gpio():
        print("ERRO CRÍTICO: Falha ao inicializar GPIO. Encerrando.")
        # Não precisa chamar cleanup aqui, pois o setup falhou.
        return # Sai da função

    try:
        # 1. Cria instância do Publicador MQTT
        print("Inicializando MQTT Publisher...")
        publisher = MQTTPublisher()

        # 2. Tenta conectar ao Broker MQTT
        if not publisher.connect():
            print("Falha ao iniciar a conexão com o broker MQTT. Encerrando.")
            # Cleanup do GPIO é necessário aqui, pois o setup foi bem-sucedido
            sensor_reader.cleanup_gpio()
            return # Sai da função

        # 3. Pausa para aguardar a conexão inicial (mantido do original)
        print("Aguardando alguns segundos para a conexão inicial com o broker MQTT...")
        time.sleep(5)

        # Verifica se a conexão foi estabelecida após a pausa (mantido do original)
        if not publisher.is_connected:
             print("Não foi possível confirmar a conexão MQTT após a espera. Encerrando.")
             publisher.disconnect()
             sensor_reader.cleanup_gpio() # Garante a limpeza do GPIO
             return # Sai da função

        # 4. Loop Principal de Leitura (Mediana) e Publicação
        print("\n--- Iniciando Loop de Leitura da Mediana e Publicação (Ctrl+C para parar) ---")
        while True:
            cycle_start_time = time.time() # Marca o início do ciclo

            # --- MODIFICADO: Lê a MEDIANA da distância ---
            # Em vez de read_distance(), chamamos get_median_distance()
            median_distance_value = sensor_reader.get_median_distance()

            if median_distance_value is not None:
                # Validação básica da MEDIANA lida
                # A faixa de validação pode ser a mesma ou ajustada se necessário
                if 5 < median_distance_value < 400:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Válida)")
                    # Cria o payload (dados a serem enviados)
                    payload_dict = {
                        # Usar a mediana aqui
                        "distancia": round(median_distance_value),
                        "created_on": datetime.now(timezone.utc).isoformat()
                    }
                    # Publica os dados formatados como JSON
                    publisher.publish_data(payload_dict)
                else:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Fora da faixa esperada, ignorando)")
            else:
                # A função get_median_distance já imprime mensagens de erro internas
                print("[Publisher Main] Falha ao obter a mediana do sensor. Pulando a publicação.")

            # --- MODIFICADO: Cálculo preciso do tempo de espera ---
            cycle_end_time = time.time()
            elapsed_time = cycle_end_time - cycle_start_time
            sleep_time = max(0, config.PUBLISH_INTERVAL_SECONDS - elapsed_time)

            print(f"Ciclo levou {elapsed_time:.2f}s. Aguardando {sleep_time:.2f}s para o próximo...")
            time.sleep(sleep_time) # Espera o tempo restante para completar o intervalo

    except KeyboardInterrupt:
        print("\nInterrupção pelo usuário (Ctrl+C) recebida. Encerrando o publisher...")
    except Exception as e:
        print(f"\nErro inesperado no loop principal do publisher: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Bloco finally garante que a limpeza será executada
        print("Encerrando a aplicação publisher...")
        # Desconecta do broker MQTT
        if publisher and publisher.is_connected: # Verifica se está conectado antes de desconectar
            print("Desconectando do MQTT Broker...")
            publisher.disconnect()
        else:
            print("Publisher MQTT não conectado ou não inicializado.")

        # Limpa os pinos GPIO utilizados pelo sensor SEMPRE no final
        # A função cleanup_gpio agora está dentro do sensor_reader
        print("Limpando os pinos GPIO...")
        sensor_reader.cleanup_gpio() # Chama a função de limpeza do módulo sensor_reader
        print("Aplicação publisher finalizada.")

# Ponto de entrada do script
if __name__ == "__main__":
    if os.geteuid() != 0:
         print("AVISO: Este script pode precisar de permissões de root (sudo) para acessar os pinos GPIO.")

    run_publisher_with_sensor()