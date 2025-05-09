import sensor_reader
import os
import time
from datetime import datetime
from database_handler import DatabaseHandler

def run_publisher_with_sensor():
    """Função principal para executar o ciclo de leitura da MEDIANA do sensor e publicação via MQTT."""

    # --- Inicializar GPIO ---
    print("Inicializando GPIO via sensor_reader...")
    if not sensor_reader.setup_gpio():
        print("ERRO CRÍTICO: Falha ao inicializar GPIO. Encerrando.")
        return

    try:

        while True:

            # Lê a MEDIANA da distância
            median_distance_value = sensor_reader.get_median_distance()

            if median_distance_value is not None:
                # Validação básica da MEDIANA lida
                if os.getenv("MIN_NIVEL") < median_distance_value < os.getenv("MAX_NIVEL"):
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Válida)")

                    created_on = datetime.now().isoformat() # Usa o timezone UTC e formato ISO
                    DatabaseHandler().insert_reading(median_distance_value, created_on)
                else:
                    print(f"Mediana do sensor: {median_distance_value:.1f} cm (Fora da faixa esperada, ignorando)")
            else:
                print("[Publisher Main] Falha ao obter a mediana do sensor. Pulando a publicação.")

            sleep_time = os.getenv("PUBLISH_INTERVAL_SECONDS") 
            time.sleep(sleep_time) # Aguarda o intervalo definido antes de repetir o ciclo

    except Exception:
        print("ERRO CRÍTICO: Falha inesperada no loop principal do publicador.")
        import traceback
        traceback.print_exc()

run_publisher_with_sensor()
