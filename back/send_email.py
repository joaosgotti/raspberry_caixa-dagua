# send_email.py
import smtplib
import ssl
import os
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

def send_backup_email(attachment_path, recipient_email, subject):
    """Envia um email com o arquivo de backup anexado."""

    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD") # Use senha de aplicativo para Gmail/Outlook
    smtp_server = os.getenv("SMTP_SERVER") # Ex: smtp.gmail.com, smtp.office365.com
    smtp_port_str = os.getenv("SMTP_PORT", "587") # Porta padrão para TLS

    # --- Validação das variáveis de ambiente ---
    if not all([sender_email, sender_password, smtp_server, recipient_email]):
        print("ERRO: Variáveis de ambiente SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, ou destinatário não definidas.")
        return False

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        print(f"ERRO: SMTP_PORT ('{smtp_port_str}') não é um número válido.")
        return False

    if not os.path.exists(attachment_path):
        print(f"ERRO: Arquivo de anexo não encontrado: {attachment_path}")
        return False

    # --- Criação da Mensagem ---
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    # Corpo do email
    body = f"Backup do banco de dados realizado em {formatdate(localtime=True)}.\n\nArquivo anexado."
    msg.attach(MIMEText(body))

    # Anexo
    try:
        with open(attachment_path, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=os.path.basename(attachment_path)
            )
        # Adiciona header para o anexo
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)
    except Exception as e:
        print(f"ERRO ao anexar o arquivo '{attachment_path}': {e}")
        return False

    # --- Envio do Email ---
    context = ssl.create_default_context() # Para conexão segura TLS
    server = None
    try:
        print(f"Conectando ao servidor SMTP {smtp_server}:{smtp_port}...")
        # Tenta conexão STARTTLS (mais comum)
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.ehlo() # Can be omitted
        server.starttls(context=context) # Secure the connection
        server.ehlo() # Can be omitted
        print("Conectado via TLS. Autenticando...")
        server.login(sender_email, sender_password)
        print("Autenticado. Enviando email...")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email enviado com sucesso para {recipient_email}!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("ERRO: Falha na autenticação SMTP. Verifique SENDER_EMAIL e SENDER_PASSWORD.")
        return False
    except smtplib.SMTPConnectError:
         print(f"ERRO: Não foi possível conectar ao servidor SMTP {smtp_server}:{smtp_port}.")
         return False
    except smtplib.SMTPServerDisconnected:
         print("ERRO: Servidor SMTP desconectou inesperadamente.")
         return False
    except Exception as e:
        print(f"ERRO inesperado durante o envio do email: {e}")
        return False
    finally:
        if server:
            try:
                server.quit()
                print("Conexão SMTP fechada.")
            except Exception:
                 print("Aviso: Erro ao fechar conexão SMTP.")


if __name__ == "__main__":
    # Permite testar o script diretamente: python send_email.py /caminho/arquivo.gz email@destino.com "Assunto Teste"
    if len(sys.argv) != 4:
        print("Uso: python send_email.py <caminho_anexo> <email_destinatario> <assunto>")
        sys.exit(1)

    attachment = sys.argv[1]
    recipient = sys.argv[2]
    email_subject = sys.argv[3]

    # Carrega variáveis de ambiente se estiver testando localmente
    from dotenv import load_dotenv
    print("Carregando .env para teste local...")
    load_dotenv()

    if send_backup_email(attachment, recipient, email_subject):
        sys.exit(0) # Sucesso
    else:
        sys.exit(1) # Falha