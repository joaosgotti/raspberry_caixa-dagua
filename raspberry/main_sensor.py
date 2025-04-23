# main_sensor.py
import time
import statistics
import sys
import config # Carrega todas as configurações e constantes
# --- Dependências Externas ---
try:
    from sensor_hc_sr04 import SensorDistancia
    from mqtt_publisher import MQTTHandler
    import RPi.GPIO
except ImportError as e:
    print(f"Erro: Dependência não encontrada - {e}")
    print("No Raspberry Pi, instale: pip install paho-mqtt RPi.GPIO python-dotenv")
    sys.exit(1)


def run_sensor_loop(sensor: SensorDistancia, mqtt: MQTTHandler):
    """Loop principal para medir, calcular mediana e publicar."""
    print("\n--- Iniciando Loop Principal de Medição ---")
    while True:
        try:
            # 1. Verificar Conexão MQTT antes de medir
            if not mqtt.is_connected:
                print("[Main Sensor] MQTT desconectado. Aguardando reconexão automática...")
                # O loop_start tentará reconectar em background
                time.sleep(5) # Espera antes de verificar novamente
                continue # Volta ao início do loop while

            # 2. Coletar Leituras do Sensor
            leituras_validas = []
            print(f"\n[Main Sensor] Coletando {config.NUM_LEITURAS_MEDIANA} leituras...")
            for i in range(config.NUM_LEITURAS_MEDIANA):
                # Medir distância
                dist = sensor.medir()

                # Validar e adicionar à lista
                if dist is not None and config.DISTANCIA_MIN_VALIDA_CM <= dist <= config.DISTANCIA_MAX_VALIDA_CM:
                    leituras_validas.append(dist)
                    print(f"  Leitura {i+1}/{config.NUM_LEITURAS_MEDIANA}: {dist:.1f} cm (Válida)")
                else:
                    # Log opcional de leituras inválidas/timeouts
                    status = "Timeout/Erro" if dist is None else f"{dist:.1f} cm (Inválida)"
                    print(f"  Leitura {i+1}/{config.NUM_LEITURAS_MEDIANA}: {status}")
                    pass # Ignora silenciosamente

                # Pausa entre leituras individuais
                time.sleep(config.INTERVALO_ENTRE_LEITURAS_MS / 1000.0)

            # 3. Calcular Mediana e Publicar (se houver leituras suficientes)
            # Usar pelo menos 3 leituras para uma mediana mais estável
            if len(leituras_validas) >= 3:
                mediana = statistics.median(leituras_validas)
                print(f"[Main Sensor] Leituras válidas: {len(leituras_validas)}/{config.NUM_LEITURAS_MEDIANA}. Mediana: {mediana:.1f} cm -> Publicando...")
                mqtt.publish_distancia(mediana)
            else:
                print(f"[Main Sensor] Leituras válidas insuficientes ({len(leituras_validas)} de {config.NUM_LEITURAS_MEDIANA}). Pulando publicação.")

            # 4. Aguardar o próximo ciclo de publicação
            print(f"[Main Sensor] Aguardando {config.INTERVALO_PUBLICACAO_S} segundos...")
            time.sleep(config.INTERVALO_PUBLICACAO_S)

        except Exception as e:
            print(f"\n[Main Sensor] Erro inesperado no loop principal: {e}")
            print("[Main Sensor] Tentando continuar em 10 segundos...")
            time.sleep(10) # Pausa antes de tentar continuar o loop

# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    print("--- Iniciando Aplicação do Sensor ---")
    if not config.check_gpio_config(): # Verifica config GPIO (apenas imprime por enquanto)
         # Adicionar validações reais se necessário
         pass

    sensor = None
    mqtt = None
    try:
        # Inicializa os componentes
        sensor = SensorDistancia()
        mqtt = MQTTHandler()

        # Tenta conectar ao MQTT
        if not mqtt.connect():
             print("[Main Sensor] Não foi possível conectar ao MQTT na inicialização. Verifique rede/credenciais. Encerrando.")
             # Limpeza necessária mesmo se a conexão falhar
             if sensor:
                 sensor.cleanup()
             sys.exit(1) # Sai com código de erro

        # Inicia o loop principal de medição e publicação
        run_sensor_loop(sensor, mqtt)

    except KeyboardInterrupt:
        print("\n[Main Sensor] Interrupção pelo usuário detectada. Encerrando...")
    except Exception as e:
        # Captura exceções que podem ocorrer durante a inicialização
        print(f"\n[Main Sensor] Erro crítico durante a inicialização ou execução: {e}")
    finally:
        print("\n--- Iniciando Limpeza Final (Sensor) ---")
        # Garante que os recursos sejam liberados na ordem correta
        if mqtt:
            mqtt.disconnect()
        if sensor:
            sensor.cleanup()
        print("[Main Sensor] Programa finalizado.")