import os
import imaplib
import email
from email.header import decode_header
import requests

# Carrega as credenciais das variáveis de ambiente configuradas no GitHub
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

IMAP_SERVER = "imap.gmail.com"

# Critérios de busca direta no Gmail
TERMOS_BUSCA = [
    'FROM "selecao.net.br"',
    'FROM "cesgranrio.org.br"',
    'FROM "ufg.br"',
    'SUBJECT "concurso"',
    'SUBJECT "coremu"',
    'SUBJECT "senar"'
]

def enviar_telegram(mensagem: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return False

def decodificar_campo(campo):
    if not campo:
        return ""
    try:
        partes = decode_header(campo)
        res = []
        for texto, charset in partes:
            if isinstance(texto, bytes):
                res.append(texto.decode(charset or 'utf-8', errors='ignore'))
            else:
                res.append(str(texto))
        return "".join(res)
    except:
        return str(campo)

def buscar_e_notificar():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, EMAIL_USER, EMAIL_PASS]):
        print("Erro: Variáveis de ambiente faltando nas configurações do repositório.")
        return

    print("Conectando ao Gmail...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")

        todos_encontrados = set()

        # Busca apenas mensagens NÃO LIDAS para evitar spams contínuos a cada ciclo
        for termo in TERMOS_BUSCA:
            consulta = f"UNSEEN {termo}"
            status, dados = mail.search(None, consulta)
            if status == "OK" and dados[0]:
                for id_msg in dados[0].split():
                    todos_encontrados.add(id_msg)

        if not todos_encontrados:
            print("Nenhum novo e-mail não lido correspondente encontrado.")
            mail.logout()
            return

        ids_ordenados = sorted(list(todos_encontrados), key=lambda x: int(x))
        print(f"{len(ids_ordenados)} novo(s) e-mail(s) encontrado(s)!")

        for email_id in ids_ordenados:
            res, dados = mail.fetch(email_id, "(RFC822)")
            if res != "OK":
                continue

            msg = email.message_from_bytes(dados[0][1])
            remetente = decodificar_campo(msg.get("From"))
            assunto = decodificar_campo(msg.get("Subject"))
            data_envio = msg.get("Date", "Desconhecida")

            texto = (
                f"📬 *Novo E-mail de Concurso/Seleção!*\n\n"
                f"*De:* `{remetente}`\n"
                f"*Assunto:* {assunto}\n"
                f"*Data:* {data_envio}"
            )
            
            if enviar_telegram(texto):
                print(f"Notificação enviada: {assunto}")
                # Marca o e-mail como lido para não notificar de novo no próximo agendamento
                mail.store(email_id, '+FLAGS', '\\Seen')

        mail.logout()
        print("Verificação concluída!")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    buscar_e_notificar()
