import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

def send_notification_email_sync(recipient_emails: list, subject: str, html_content: str):
    """Envoie un email de manière synchrone."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] SMTP credentials missing, email not sent.")
        return

    if not recipient_emails:
        print("[EMAIL] No recipients provided, email not sent.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"LEFAXEUR <{SMTP_USER}>"
        msg["To"] = ", ".join(recipient_emails)

        part = MIMEText(html_content, "html")
        msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, recipient_emails, msg.as_string())
        server.quit()
        print(f"[EMAIL] Notification sent to {len(recipient_emails)} recipients.")
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")

async def send_notification_email(cycle: str, subject: str, message: str):
    """
    Récupère les emails des utilisateurs concernés par le cycle et envoie l'email.
    Cette fonction est destinée à être appelée via BackgroundTasks.
    """
    from database.db import get_db
    import asyncio
    db = get_db()
    
    # Trouver les utilisateurs de ce cycle (ou tous si c'est "Général")
    query = {}
    if cycle and cycle != "Général":
        query["cycle"] = cycle
    
    cursor = db.users.find(query, {"email": 1, "_id": 0})
    emails = []
    async for user in cursor:
        if "email" in user and user["email"]:
            emails.append(user["email"])
            
    if not emails:
        return
        
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background-color: #f4f4f4; padding: 20px;">
          <h2 style="color: #1a56db;">Nouvelle notification - LEFAXEUR</h2>
          <div style="background-color: #fff; padding: 20px; border-radius: 5px;">
            <p>{message}</p>
            <br>
            <p>Connectez-vous sur la plateforme pour consulter cette nouveauté.</p>
          </div>
          <p style="font-size: 12px; color: #777; margin-top: 20px;">Ceci est un email automatique, merci de ne pas y répondre.</p>
        </div>
      </body>
    </html>
    """
    
    # Exécuter l'envoi synchrone dans un thread séparé pour ne pas bloquer l'asyncio
    await asyncio.to_thread(send_notification_email_sync, emails, subject, html_content)
