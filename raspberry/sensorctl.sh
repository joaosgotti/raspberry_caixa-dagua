#!/bin/bash

# --- Configuração ---
SCRIPT_NAME="leitura-sensor.py"
SESSION_NAME="caixa_dagua_sensor" # Nome para a sessão screen
# Obtém o diretório onde este script shell está localizado
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PYTHON_SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"
# --- Fim da Configuração ---

# Função para verificar se a sessão screen está rodando
is_running() {
  screen -ls | grep -q "$SESSION_NAME"
}

# Função para iniciar o sensor
start_sensor() {
  if is_running; then
    echo "O script do sensor já está rodando na sessão screen '$SESSION_NAME'."
    echo "Para ver a saída, use: screen -r $SESSION_NAME"
  else
    echo "Iniciando o script '$SCRIPT_NAME' na sessão screen '$SESSION_NAME'..."
    # Verifica se o script Python existe
    if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
        echo "Erro: Script Python '$PYTHON_SCRIPT_PATH' não encontrado!"
        exit 1
    fi
    # Inicia o screen em modo detached (-d), cria (-m), nomeia (-S) e executa o comando
    # O comando é executado com sudo e python3
    screen -dmS "$SESSION_NAME" sudo python3 "$PYTHON_SCRIPT_PATH"
    sleep 1 # Pequena pausa para dar tempo ao screen de iniciar
    if is_running; then
      echo "Script iniciado com sucesso em background."
      echo "Para ver a saída, use: screen -r $SESSION_NAME"
      echo "(Dentro do screen, use Ctrl+A, D para desanexar sem parar o script)"
    else
      echo "Erro ao iniciar a sessão screen '$SESSION_NAME'. Verifique as permissões ou logs."
    fi
  fi
}

# Função para parar o sensor
stop_sensor() {
  if is_running; then
    echo "Parando a sessão screen '$SESSION_NAME'..."
    # Envia o comando 'quit' para a sessão screen específica
    screen -X -S "$SESSION_NAME" quit
    sleep 1 # Pausa para terminação
    if is_running; then
        echo "Falha ao parar a sessão. Tentando forçar com kill (pode levar alguns segundos)..."
        # Tenta matar o processo se o quit falhou (abordagem mais agressiva)
        pkill -f "SCREEN.*$SESSION_NAME.*$SCRIPT_NAME"
        sleep 2
        if is_running; then
            echo "Erro: Não foi possível parar a sessão '$SESSION_NAME'. Verifique manualmente."
        else
            echo "Sessão forçada a parar."
        fi
    else
        echo "Sessão screen '$SESSION_NAME' parada."
    fi
  else
    echo "O script do sensor não está rodando na sessão screen '$SESSION_NAME'."
  fi
}

# Função para ver o status/logs
show_status() {
  if is_running; then
    echo "O script do sensor está RODANDO na sessão screen '$SESSION_NAME'."
    echo "Para anexar e ver a saída ao vivo, use: screen -r $SESSION_NAME"
    echo "(Use Ctrl+A, D para desanexar novamente)"
  else
    echo "O script do sensor NÃO está rodando."
    # Verifica se há um nohup.out de execuções anteriores (opcional)
    # if [ -f "$SCRIPT_DIR/nohup.out" ]; then
    #   echo "Últimas linhas do log nohup.out (se houver):"
    #   tail "$SCRIPT_DIR/nohup.out"
    # fi
  fi
}

# Processa os argumentos da linha de comando
case "$1" in
  start)
    start_sensor
    ;;
  stop)
    stop_sensor
    ;;
  restart)
    stop_sensor
    start_sensor
    ;;
  status)
    show_status
    ;;
  log | attach | view) # Atalho para ver a saída
    if is_running; then
        echo "Anexando à sessão '$SESSION_NAME'... (Use Ctrl+A, D para desanexar)"
        screen -r "$SESSION_NAME"
    else
        echo "O script não está rodando. Não há sessão para anexar."
        # show_status # Mostra status se não estiver rodando
    fi
    ;;
  *)
    echo "Uso: $0 {start|stop|restart|status|log}"
    exit 1
    ;;
esac

exit 0