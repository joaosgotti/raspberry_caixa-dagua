#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# main_publisher.py
# Script principal para ler a MEDIANA do sensor HC-SR04 e publicar via MQTT.
# Utiliza os módulos sensor_reader (versão com mediana) e mqtt_publisher.

import time
import json
from datetime import datetime, timezone # timezone ainda é útil para UTC como fallback
import sys
import os
try:
    # Importa ZoneInfo para lidar com fusos horários específicos
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Fallback para pytz se zoneinfo não estiver disponível (Python < 3.9)
    # Nesse caso, você precisaria instalar: pip install pytz
    try:
        import pytz
        print("Aviso: Módulo zoneinfo não encontrado (Python < 3.9?). Usando pytz como alternativa.")
        # Define uma função compatível para obter o objeto de timezone
        def get_zoneinfo(tz_name):
            return pytz.timezone(tz_name)
        ZoneInfoNotFoundError = pytz.exceptions.UnknownTimeZoneError # Define a exceção compatível
    except ImportError:
        print("ERRO: Nem zoneinfo nem pytz foram encontrados. Timestamps usarão UTC.")
        # Define funções dummy para não quebrar o código, mas usará UTC
        def get_zoneinfo(tz_name): return timezone.utc
        class ZoneInfoNotFoundError(Exception): pass


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

# --- Constante para o fuso horário desejado ---
TARGET_TIMEZONE = "America/Recife"

def run_publisher_with_sensor():
    """Função principal para executar o ciclo de leitura da MEDIANA do sensor e publicação via MQTT."""
    print(f"--- Iniciando Aplicação Publisher (Fuso Horário: {TARGET_TIMEZONE}) ---")
    publisher = None # Inicializa publisher como None para o finally
    recife_tz = None # Inicializa o objeto de timezone

    # --- Tenta carregar o fuso horário ---
    try:
        # Usa ZoneInfo (Python >= 3.9) ou a função de fallback get_zoneinfo (pytz)
        if 'ZoneInfo' in globals(): # Verifica se ZoneInfo foi importado com sucesso
            recife_tz = ZoneInfo(TARGET_TIMEZONE)
        else: # Usa a função get_zoneinfo (que pode ser pytz ou um fallback UTC)
             recife_tz = get_zoneinfo(TARGET_TIMEZONE)
        print(f"Fuso horário '{TARGET_TIMEZONE}' carregado com sucesso.")
    except ZoneInfoNotFoundError:
        print(f"ERRO: Fuso horário '{TARGET_TIMEZONE}' não encontrado.")
        print("Verifique se o pacote 'tzdata' está instalado (sudo apt install tzdata).")
        print("Usando UTC como fallback para timestamps.")
        recife_tz = timezone.utc # Define UTC como fallback
    except Exception as tz_err:
         print(f"ERRO inesperado ao carregar fuso horário: {tz_err}")
         print("Usando UTC como fallback para timestamps.")
         recife_tz = timezone.utc # Define UTC como fallback


    # --- PASSO NOVO: Inicializar GPIO ---
    print("Inicializando GPIO via sensor_reader...")
    if not sensor_reader.setup_gpio():
        print("ERRO CRÍTICO: Falha ao inicializar GPIO. Encerrando.")
        return

    try:
        # 1. Cria instância do Publicador MQTT
        print("Inicializando MQTT Publisher...")
        publisher = MQTTPublisher()

        # 2. Tenta conectar ao Broker MQTT
        if not publisher.connect():
            print("Falha ao iniciar a conexão com o broker MQTT. Encerrando.")
            sensor_reader.cleanup_gpio()
            return

        # 3. Pausa para aguardar a conexão inicial
        print("Aguardando alguns segundos para a conexão inicial com o broker MQTT...")
        time.sleep(5)

        # Verifica se a conexão foi estabelecida após a pausa
        if not publisher.is_connected:
             print("Não foi possível confirmar a conexão MQTT após a espera. Encerrando.")
             publisher.disconnect()
             sensor_reader.cleanup_gpio()
             return

        # 4. Loop Principal de Leitura (Mediana) e Publicação
        print("\n--- Iniciando Loop de Leitura da Mediana e Publicação (Ctrl+C para parar) ---")
        while True:
            cycle_start_time = time.time()

            # Lê a MEDIANA da distância
            median_distance_value = sensor_reader.get_median_distance()

            if median_distance_value is not None:
                # Validação básica da MEDIANA lida
                if 5 < median_distance_value < 400:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Válida)")

                    # --- MODIFICADO: Gera timestamp no fuso horário correto ---
                    timestamp_now_local = datetime.now(recife_tz) # Usa o objeto de timezone carregado
                    timestamp_iso_local = timestamp_now_local.isoformat() # Gera string ISO com offset correto

                    # Cria o payload
                    payload_dict = {
                        "distancia": round(median_distance_value),
                        "created_on": timestamp_iso_local # Usa o timestamp local formatado
                    }
                    # Publica os dados formatados como JSON
                    publisher.publish_data(payload_dict)
                else:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Fora da faixa esperada, ignorando)")
            else:
                print("[Publisher Main] Falha ao obter a mediana do sensor. Pulando a publicação.")

            # Cálculo preciso do tempo de espera
            cycle_end_time = time.time()
            elapsed_time = cycle_end_time - cycle_start_time
            sleep_time = max(0, config.PUBLISH_INTERVAL_SECONDS - elapsed_time)

            print(f"Ciclo levou {elapsed_time:.2f}s. Aguardando {sleep_time:.2f}s para o próximo...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nInterrupção pelo usuário (Ctrl+C) recebida. Encerrando o publisher...")
    except Exception as e:
        print(f"\nErro inesperado no loop principal do publisher: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Encerrando a aplicação publisher...")
        if publisher and publisher.is_connected:
            print("Desconectando do MQTT Broker...")
            publisher.disconnect()
        else:
            print("Publisher MQTT não conectado ou não inicializado.")

        print("Limpando os pinos GPIO...")
        sensor_reader.cleanup_gpio()
        print("Aplicação publisher finalizada.")

# Ponto de entrada do script
if __name__ == "__main__":
    if os.geteuid() != 0:
         print("AVISO: Este script pode precisar de permissões de root (sudo) para acessar os pinos GPIO.")

    run_publisher_with_sensor()