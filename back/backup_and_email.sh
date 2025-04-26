#!/bin/bash

# Sai
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        # Usa o nome do arquivo como header
        filename = os.path.basename(attachment_path)
        part.add_header(
            'Content-Disposition',
            f"attachment; filename= {filename}",
        )
        msg.attach(part)
        print(f"Arquivo '{filename}' anexado com sucesso.")
    except FileNotFoundError:
        print(f"Erro: Arquivo de anexo '{attachment_path}' não encontrado.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler ou anexar o arquivo '{attachment_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # --- Envio do E-mail ---
    try:
        print(f"Conectando ao servidor SMTP: {smtp_host}:{smtp_port}")
        # Use smtplib.SMTP_SSL(smtp_host, smtp_port) se a porta for 465
        # Use smtplib.SMTP(smtp_host, smtp_port) para porta 587 (TLS)
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Inicia conexão segura TLS (necessário para porta 587)
        print("Conectado. Autenticando...")
        server.login(smtp_user, smtp_password)
        print("Autenticado. Enviando e-mail...")
        text = msg.as_string()
        server.sendmail(sender_email, args.to, text)
        print(f"E-mail enviado com sucesso para {args.to}!")
    except smtplib.SMTPAuthenticationError:
        print("Erro de Autenticação SMTP: Verifique usuário/senha (ou Senha de App).", file=sys.stderr)
        sys.exit(1)
    except smtplib.SMTPServerDisconnected:
         print("Erro SMTP: Servidor desconectado inesperadamente.", file=sys.stderr)
         sys.exit(1)
    except smtplib.SMTPException as e:
        print(f"Erro SMTP: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado ao enviar e-mail: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            if 'server' in locals() and server:
                server.quit()
                print("Conexão SMTP fechada.")
        except:
            pass # Ignora erros ao tentar fechar
    ```

*   **`backup_and_email.sh`**

    ```bash
    #!/bin/bash

    # Impede a execução se algum comando falhar
    set -e

    echo "--- Iniciando Script de Backup e E-mail ---"
    TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
    BACKUP_DIR="/tmp/backups" # Diretório temporário para o backup
    DB_NAME_VAR="${DB_NAME}" # Pega do ambiente
    BACKUP_FILENAME="backup_${DB_NAME_VAR}_${TIMESTAMP}.sql"
    BACKUP_FILE_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
    COMPRESSED_BACKUP_FILENAME="${BACKUP_FILENAME}.gz"
    COMPRESSED_BACKUP_FILE_PATH="${BACKUP_FILE_PATH}.gz"

    EMAIL_RECIPIENT_VAR="${EMAIL_RECIPIENT}" # Pega do ambiente

    # Validação básica das variáveis de ambiente do DB e Email
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME_VAR" ] || [ -z "$PGPASSWORD" ]; then
        echo "Erro Crítico: Variáveis de ambiente do banco de dados (DB_HOST, DB_USER, DB_PORT, DB_NAME, PGPASSWORD) não estão configuradas." >&2
        exit 1
    fi
    if [ -z "$EMAIL_RECIPIENT_VAR" ]; then
        echo "Erro Crítico: Variável de ambiente EMAIL_RECIPIENT não está configurada." >&2
        exit 1
    fi
    # (O script python fará a validação das variáveis SMTP)

    # Cria o diretório de backup se não existir
    mkdir -p "$BACKUP_DIR"
    echo "Diretório de backup: ${BACKUP_DIR}"

    # 1. Executa o pg_dump
    echo "Executando pg_dump para o banco '${DB_NAME_VAR}'..."
    # PGPASSWORD é lido automaticamente pelo pg_dump do ambiente
    pg_dump -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME_VAR" -F c -b -v -f "$BACKUP_FILE_PATH"
    # -F c -> Formato customizado (bom para comprimir e restaurar com pg_restore)
    # -b   -> Inclui blobs
    # -v   -> Verbose (mostra progresso)
    # -f   -> Arquivo de saída
    echo "pg_dump concluído. Arquivo: ${BACKUP_FILE_PATH}"

    # 2. Comprime o arquivo de backup (Opcional, mas recomendado)
    echo "Comprimindo arquivo de backup..."
    gzip "$BACKUP_FILE_PATH"
    echo "Arquivo comprimido: ${COMPRESSED_BACKUP_FILE_PATH}"

    # 3. Envia o e-mail com o backup anexado
    echo "Enviando backup por e-mail para ${EMAIL_RECIPIENT_VAR}..."
    SUBJECT="Backup BD ${DB_NAME_VAR} - ${TIMESTAMP}"
    BODY="Segue em anexo o backup do banco de dados ${DB_NAME_VAR} gerado em ${TIMESTAMP}."

    # Chama o script Python para enviar o e-mail. Se falhar, o 'set -e' parará o script.
    python3 send_email.py --to "$EMAIL_RECIPIENT_VAR" --subject "$SUBJECT" --body "$BODY" --attachment "$COMPRESSED_BACKUP_FILE_PATH"

    echo "E-mail enviado (ou tentativa feita)."

    # --- SEÇÃO PER imediatamente se um comando falhar
set -e

echo "--- Iniciando Script de Backup e Email ---"

# --- Variáveis (Lidas do Ambiente do Cron Job) ---
# DATABASE_URL é geralmente fornecido pelo Render ao conectar um DB
# Verifique o nome exato na aba Environment do seu DB ou Web Service
if [ -z "$DATABASE_URL" ]; then
  echo "ERRO FATAL: Variável de ambiente DATABASE_URL não definida!"
  exit 1
fi
if [ -z "$RECIPIENT_EMAIL" ]; then
  echo "ERRO FATAL: Variável de ambiente RECIPIENT_EMAIL não definida!"
  exit 1
fi

# Diretório temporário para o backup (dentro do container)
BACKUP_DIR="/tmp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME_GUESS=$(echo $DATABASE_URL | sed -E 's|.*\/([^?]+).*|\1|') # Tenta adivinhar nome do DB pela URL
BACKUP_FILENAME="db_backup_${DB_NAME_GUESS}_${TIMESTAMP}.sql"
BACKUP_FILE_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
COMPRESSED_FILE_PATH="${BACKUP_FILE_PATH}.gz"
EMAIL_SUBJECT="Backup Banco de Dados ${DB_NAME_GUESS} - ${TIMESTAMP}"
# Caminho para o script python (ajuste se necessário, ex: /opt/render/project/src/back/send_email.py)
PYTHON_SCRIPT_PATH="$(dirname "$0")/send_email.py" # Assume que está na mesma pasta do .sh

# --- 1. Criar o Dump do Banco de Dados ---
echo "Criando dump do banco de dados em ${BACKUP_FILE_PATH}..."
# pg_dump usa a DATABASE_URL diretamente
pg_dump "$DATABASE_URL" > "$BACKUP_FILE_PATH"
echo "Dump criado com sucesso."

# --- 2. Comprimir o Arquivo de Dump ---
echo "Comprimindo o arquivo de dump para ${COMPRESSED_FILE_PATH}..."
gzip "$BACKUP_FILE_PATH"
echo "Arquivo comprimido."

# --- 3. Enviar o Email com o Anexo ---
echo "Tentando enviar email para ${RECIPIENT_EMAIL}..."
# Chama o script Python,IGOSA: LIMPEZA DO BANCO DE DADOS ---
    # !!! DESCOMENTE AS LINHAS ABAIXO APENAS SE TIVER CERTEZA ABSOLUTA DOS RISCOS !!!
    # !!! RECOMENDO FORTEMENTE NÃO FAZER ISSO AUTOMATICAMENTE !!!
    # echo ">>> ATENÇÃO: EXECUTANDO LIMPEZA DO BANCO DE DADOS (${DB_NAME_VAR}) <<<"
    # # Escolha UMA das opções de limpeza:
    # # Opção A: TRUNCATE (rápido, reseta sequences, apaga TUDO, irreversível)
    # # psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME_VAR" -c "TRUNCATE TABLE leituras RESTART IDENTITY;"
    # # Opção B: DELETE (mais lento, não reseta sequences, apaga TUDO)
    # # psql -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME_VAR" -c "DELETE FROM leituras;"
    # echo "Limpeza do banco de dados concluída (ou tentativa feita)."
    # --- FIM DA SEÇÃO PERIGOSA ---


    # 4. Limpa o arquivo de backup local
    echo "Limpando arquivo de backup local..."
    rm "$COMPRESSED_BACKUP_FILE_PATH"
    echo "Limpeza concluída."

    echo "--- Script de Backup e E-mail Finalizado com Sucesso ---"
    exit 0
    ```

    *   Torne o script shell executável: `chmod +x backup_and_email.sh`

**4. Configurar o Render Cron Job:**

*   No dashboard do Render, clique em "New +" -> "Cron Job".
*   Conecte seu repositório Git.
*   **Name:** Dê um nome (ex: `backup-db-diario`).
*   **Region:** Escolha a mesma região dos seus outros serviços.
*   **Schedule:** Defina a frequência. Para "todo dia 1º às 3:00 da manhã (UTC)": `0 3 1 * *`
    *   Explicação do Cron: `Minuto(0-59) Hora(0-23) DiaDoMês(1-31) Mês(1-12) DiaDaSemana(0-7, 0 ou 7 é Domingo)`
    *   `*` significa "qualquer valor".
*   **Build Command:** (Ver Passo 1) Se precisar passando o caminho do arquivo comprimido, destinatário e assunto
# O script Python lerá as credenciais SENDER_* e SMTP_* do ambiente
if python3 "$PYTHON_SCRIPT_PATH" "$COMPRESSED_FILE_PATH" "$RECIPIENT_EMAIL" "$EMAIL_SUBJECT"; then
  echo "Script Python de envio de email retornou SUCESSO."

  # --- 4. LIMPEZA DO BANCO DE DADOS (OPCIONAL E ARRISCADO) ---
  # !!! DESCOMENTE AS LINHAS ABAIXO APENAS SE TIVER CERTEZA ABSOLUTA !!!
  # !!! E ENTENDER OS RISCOS. TESTE EXAUSTIVAMENTE ANTES !!!
  # echo ">>> INICIANDO LIMPEZA DO BANCO DE DADOS (APÓS ENVIO SUPOSTAMENTE BEM SUCEDIDO) <<<"
  # echo "Deletando registros da tabela 'leituras'..."
  # if psql "$DATABASE_URL" -c "DELETE FROM leituras;"; then
  #    echo "Comando DELETE executado."
  # else
  #    echo ">>> ER instalar `postgresql-client`, coloque o comando aqui (ex: `apt-get update && apt-get install -y postgresql-client`). Se não, deixe em branco ou use o build command do seu backend se ele já instala isso.
*   **Command:** `bash ./caminho/para/backup_and_email.sh` (Substitua `/caminho/para/` pelo diretório correto onde o script está no seu repositório, ex: `./back/backup_and_email.sh` se estiver dentro da pasta `back`).
*   **Environment Variables:** Adicione TODAS estas variáveis:
    *   `DB_HOST`: (Host do seu DB no Render - veja nas infos de conexão do DB)
    *   `DB_USER`: (Usuário do seu DB no Render)
    *   `DB_PORT`: (Porta do seu DB no Render, geralmente 5432)
    *   `DB_NAME`: (Nome do seu DB no Render)
    *   `PGPASSWORD`: **IMPORTANTE!** (Senha do seu DB no Render. O Render trata variáveis com `PASSWORD` no nome de forma segura).
    *   `SMTP_HOST`: (Ex: `smtp.gmail.com`)
    *   `SMTP_PORT`: (Ex: `587`)
    *   `SMTP_USER`: (Seu usuário/email SMTP)
    *   `SMTP_PASSWORD`: (Sua senha de App ou senha/chave API SMTP)
    *   `SENDER_EMAIL`: (OpcRO ao executar comando DELETE no banco de dados! <<<"
  # fi
  # echo ">>> FIM DA LIMPEZA DO BANCO DE DADOS <<<"

else
  echo ">>> ERRO: Script Python de envio de email retornou FALHA. <<<"
  echo ">>> NENHUMA LIMPEZA DO BANCO DE DADOS SERÁ REALIZADA. <<<"
  # Limpa apenas o arquivo de backup local em caso de falha no email
  echo "Limpando arquivo de backup local (${COMPRESSED_FILE_PATH})..."
  rm -f "$COMPRESSED_FILE_PATH"
  exit 1 # Sai do script com erro para o Render saber que falhou
fi

# --- ional, seu e-mail remetente se diferente do usuário)
    *   `EMAIL_RECIPIENT`: (O e-mail que receberá o backup)
*   Clique em "Create Cron Job".

**Considerações Finais:**

*   **Teste:** Teste o Cron Job manualmente no Render ("Run" ou "Trigger") e verifique se o e-mail chega e o backup está correto ANTES de confiar no agendamento automático. Verifique os logs do Cron Job no Render para erros.
*   **Limpeza:** **Pense MUITO BEM** antes de descom5. Limpar Arquivo de Backup Local (Após sucesso) ---
echo "Limpando arquivo de backup local (${COMPRESSED_FILE_PATH})..."
rm -f "$COMPRESSED_FILE_PATH"

echo "--- Script de Backup e Email concluído com sucesso! ---"
exit 0