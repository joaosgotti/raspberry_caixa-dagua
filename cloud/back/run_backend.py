import subprocess
import sys
import time
import os
import signal

# --- Configuração ---
# Backend
LISTENER_SCRIPT = "mqtt_listener.py"
# API_SCRIPT = "api.py" # Não precisamos mais do nome do script diretamente
API_MODULE = "api" # Nome do módulo Python (api.py -> api)
API_VARIABLE = "app" # Nome da variável da instância FastAPI/Flask dentro do módulo
API_HOST = "0.0.0.0" # Ouvir em todas as interfaces
API_PORT = "8000" # Porta da API
# Frontend
FRONTEND_DIR = "front"
FRONTEND_MANAGER = "yarn"
FRONTEND_COMMAND = "dev"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LISTENER_PATH = os.path.join(SCRIPT_DIR, LISTENER_SCRIPT)
# API_PATH = os.path.join(SCRIPT_DIR, API_SCRIPT) # Não usamos mais
FRONTEND_DIR_PATH = os.path.join(SCRIPT_DIR, '..', FRONTEND_DIR) # Ajustado para subir um nível e entrar em front

processes = []

# --- signal_handler (sem alterações) ---
def signal_handler(sig, frame):
    print("\n" + "-"*50)
    print("Recebido sinal de interrupção. Parando todos os processos...")
    for p_info in reversed(processes):
        pid = p_info.get('pid')
        name = p_info.get('name')
        process_obj = p_info.get('process')
        if process_obj and process_obj.poll() is None:
            print(f"Parando {name} (PID: {pid})...")
            try:
                process_obj.terminate()
                try:
                   process_obj.wait(timeout=3)
                   print(f"{name} parado.")
                except subprocess.TimeoutExpired:
                   print(f"{name} não terminou, forçando kill...")
                   process_obj.kill()
                   print(f"{name} forçado a parar.")
            except Exception as e:
                print(f"Erro ao tentar parar {name} (PID: {pid}): {e}")
        elif pid:
            print(f"{name} (PID: {pid}) já havia parado ou não foi iniciado corretamente.")
    print("-" * 50)
    print("Processos parados. Saindo.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("Iniciando Backend (MQTT Listener, API) e Frontend (React Dev Server)...")
print("Os logs de todos aparecerão abaixo.")
print("Pressione Ctrl+C para parar TODOS os processos.")
print("-" * 50)

try:
    # Verifica se os scripts/pastas existem
    if not os.path.isfile(LISTENER_PATH):
        raise FileNotFoundError(f"Erro: Script MQTT Listener '{LISTENER_PATH}' não encontrado!")
    # Verifica se o módulo API existe (simplificado, assume que está na mesma pasta)
    if not os.path.isfile(os.path.join(SCRIPT_DIR, f"{API_MODULE}.py")):
         raise FileNotFoundError(f"Erro: Arquivo API '{API_MODULE}.py' não encontrado!")
    if not os.path.isdir(FRONTEND_DIR_PATH):
        raise FileNotFoundError(f"Erro: Pasta do Frontend '{FRONTEND_DIR_PATH}' não encontrada!")
    if not os.path.isfile(os.path.join(FRONTEND_DIR_PATH, 'package.json')):
         print(f"Aviso: 'package.json' não encontrado em '{FRONTEND_DIR_PATH}'. O comando '{FRONTEND_MANAGER} run {FRONTEND_COMMAND}' pode falhar.")

    # --- Inicia MQTT Listener ---
    print("[Backend] Iniciando MQTT Listener...")
    listener_process = subprocess.Popen([sys.executable, LISTENER_PATH], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    processes.append({'name': 'MQTT Listener', 'process': listener_process, 'pid': listener_process.pid})
    print(f"[Backend] MQTT Listener iniciado com PID: {listener_process.pid}")
    time.sleep(0.5)

    # --- Inicia API com Uvicorn ---
    print(f"[Backend] Iniciando API ({API_MODULE}:{API_VARIABLE}) com Uvicorn...")
    # Comando para rodar uvicorn usando o interpretador python atual
    api_cmd_list = [
        sys.executable, # Garante usar o python correto
        "-m", "uvicorn", # Executa uvicorn como módulo
        f"{API_MODULE}:{API_VARIABLE}", # Especifica arquivo:variável_app
        "--host", API_HOST,
        "--port", API_PORT,
        # "--reload" # Descomente para desenvolvimento se quiser auto-reload
    ]
    # A API também precisa rodar no diretório correto se importar outros arquivos locais
    api_process = subprocess.Popen(api_cmd_list,
                                   cwd=SCRIPT_DIR, # Roda a partir da pasta onde api.py está
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
    processes.append({'name': 'API Server (Uvicorn)', 'process': api_process, 'pid': api_process.pid})
    print(f"[Backend] API iniciada com PID: {api_process.pid}")
    time.sleep(1) # Dar um tempo maior para a API iniciar

    # --- Inicia Frontend ---
    print(f"[Frontend] Iniciando '{FRONTEND_MANAGER} run {FRONTEND_COMMAND}' em '{FRONTEND_DIR_PATH}'...")
    frontend_cmd_list = []
    if sys.platform == "win32":
        frontend_cmd = f"{FRONTEND_MANAGER}.cmd"
    else:
        frontend_cmd = FRONTEND_MANAGER
    frontend_cmd_list = [frontend_cmd, 'run', FRONTEND_COMMAND]

    frontend_process = subprocess.Popen(
        frontend_cmd_list,
        cwd=FRONTEND_DIR_PATH,
        shell=True, # Mantido para Windows
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    processes.append({'name': 'Frontend Dev Server', 'process': frontend_process, 'pid': frontend_process.pid})
    print(f"[Frontend] Servidor iniciado com PID: {frontend_process.pid} (Processo: {FRONTEND_MANAGER})")

    # --- Mantém Script Rodando ---
    print("-" * 50)
    print("Todos os processos iniciados. Pressione Ctrl+C para parar.")
    while True:
        for p_info in processes:
            process_obj = p_info.get('process')
            name = p_info.get('name')
            if process_obj and process_obj.poll() is not None:
                print(f"\n[AVISO] Processo '{name}' (PID: {p_info.get('pid')}) terminou inesperadamente com código {process_obj.returncode}.")
                print("Parando os outros processos...")
                signal_handler(None, None)
        time.sleep(2)

except FileNotFoundError as e:
    print(f"\nErro: {e}")
    print("Verifique os nomes e caminhos dos scripts/pastas na configuração.")
except Exception as e:
    print(f"\nErro geral ao iniciar os scripts: {e}")
    signal_handler(None, None)