#!/bin/bash

# --- Configuração ---
SCRIPT_NAME="leitura-sensor.py"
SESSION_NAME="caixa_dagua_sensor" # Nome da sessão screen
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PYTHON_SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_NAME"
# --- Fim da Configuração ---

# Função para mostrar o menu de uso
show_usage() {
  echo "" # Linha em branco para separar
  echo "--------------------------------------------------"
  echo "Script para controlar o sensor da caixa d'água."
  echo "Uso: $0 {start|stop|view}"
  echo "  start : Inicia o sensor em background."
  echo "  stop  : Para o sensor."
  echo "  view  : Mostra a saída atual (Ctrl+A, D para sair)."
  echo "--------------------------------------------------"
}

# Verifica se a sessão screen específica está rodando
is_running() {
  screen -ls | grep -q "\.$SESSION_NAME"
}

# Ação baseada no argumento ($1)
ACTION_PERFORMED=0 # Flag para saber se alguma ação foi feita

case "$1" in
  start)
    ACTION_PERFORMED=1
    if is_running; then
      echo "Sensor já está rodando na sessão '$SESSION_NAME'."
    else
      echo "Iniciando sensor em background via screen ('$SESSION_NAME')..."
      if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
          echo "Erro: Script Python '$PYTHON_SCRIPT_PATH' não encontrado!"
          exit 1
      fi
      screen -dmS "$SESSION_NAME" sudo python3 "$PYTHON_SCRIPT_PATH"
      sleep 1
      if is_running; then
          echo "Sensor iniciado."
      else
          echo "Erro ao iniciar o sensor no screen."
      fi
    fi
    ;;
  stop)
    ACTION_PERFORMED=1
    if is_running; then
      echo "Parando sessão screen '$SESSION_NAME'..."
      screen -X -S "$SESSION_NAME" quit
      sleep 1
       if ! is_running; then
            echo "Sensor parado."
       else
            echo "Falha ao parar. Tente manualmente com 'screen -ls' e 'kill'."
       fi
    else
      echo "Sensor não estava rodando."
    fi
    ;;
  view|log|attach)
    ACTION_PERFORMED=1 # Consideramos view como uma ação
    if is_running; then
      echo "Anexando à sessão '$SESSION_NAME'... (Use Ctrl+A, D para desanexar)"
      # Executa o screen no modo de reanexar - O script shell pausa aqui
      screen -r "$SESSION_NAME"
      # Após desanexar do screen, o script shell continua daqui
      echo "Desanexado da sessão '$SESSION_NAME'."
    else
      echo "Sensor não está rodando. Nada para visualizar."
    fi
    ;;
  *)
    # Nenhuma ação válida foi fornecida OU nenhum argumento foi dado
    # A função show_usage será chamada no final de qualquer forma
    ;;
esac

# Mostra o menu de uso sempre, exceto se um erro fatal ocorreu antes
show_usage

exit 0