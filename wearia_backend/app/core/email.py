import os
import secrets
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger("wearia.otp")

def generate_otp() -> str:
    """Génère un code OTP sécurisé à 6 chiffres."""
    return f"{secrets.randbelow(900000) + 100000}"

def send_otp_email(email: str, code: str, purpose: str = "REGISTER") -> bool:
    """
    Envoie le code OTP par email avec template HTML soigné.
    Si SMTP n'est pas configuré ou échoue, le code est journalisé
    de manière très visible dans la console du serveur pour les tests et la démo.
    """
    action_fr = "activer votre compte" if purpose.upper() == "REGISTER" else "autoriser votre connexion"
    subject = f"Wearia - Code de vérification : {code}"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f7f7f9; margin: 0; padding: 0; }}
    .container {{ max-width: 500px; margin: 30px auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #ebebeb; }}
    .header {{ background-color: #121212; padding: 32px 20px; text-align: center; }}
    .logo {{ color: #ffffff; font-size: 26px; font-weight: 800; letter-spacing: 4px; margin: 0; text-transform: uppercase; }}
    .body {{ padding: 36px 32px; text-align: center; }}
    .title {{ font-size: 20px; font-weight: 700; color: #1a1a1a; margin-top: 0; }}
    .desc {{ font-size: 15px; color: #666666; line-height: 1.6; margin-bottom: 24px; }}
    .otp-box {{ background-color: #f4f4f6; border-radius: 12px; padding: 18px 24px; display: inline-block; margin: 12px 0 24px 0; letter-spacing: 8px; font-size: 34px; font-weight: 800; color: #000000; font-family: 'Courier New', Courier, monospace; }}
    .validity {{ font-size: 13px; color: #999999; margin-top: 0; }}
    .footer {{ background-color: #fafafa; padding: 20px; text-align: center; font-size: 12px; color: #aaaaaa; border-top: 1px solid #f0f0f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="logo">W E A R I A</h1>
    </div>
    <div class="body">
      <h2 class="title">Vérification de sécurité</h2>
      <p class="desc">Vous avez demandé à {action_fr} sur l'application <b>Wearia</b>.<br>Veuillez renseigner le code à usage unique ci-dessous :</p>
      <div class="otp-box">{code}</div>
      <p class="validity">Ce code est confidentiel et expire dans <b>10 minutes</b>.</p>
    </div>
    <div class="footer">
      Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email en toute sécurité.<br>&copy; 2026 Wearia Inc. — Smart Wardrobe & Outfit Recommendation
    </div>
  </div>
</body>
</html>
"""

    text_content = (
        f"Wearia - Code de vérification\n\n"
        f"Votre code pour {action_fr} est : {code}\n\n"
        f"Ce code expire dans 10 minutes.\n"
        f"Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
    )

    # 1. Toujours afficher de manière très visible dans la console du serveur backend
    print("\n" + "=" * 70)
    print(f" [WEARIA EMAIL OTP] Code de sécurité généré")
    print(f" 📧 Destinataire : {email}")
    print(f" 🎯 Action       : {purpose.upper()} ({action_fr})")
    print(f" 🔑 CODE OTP     : {code}  (Valide 10 minutes)")
    print("=" * 70 + "\n")

    logger.info(f"[OTP] Code envoyé pour {email} (purpose: {purpose}) : {code}")

    # 2. Si SMTP est configuré, tenter l'envoi réel de l'email
    if settings.SMTP_HOST and settings.SMTP_USER:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg["To"] = email

            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, [email], msg.as_string())

            logger.info(f"[OTP] Email SMTP délivré avec succès à {email}")
            return True
        except Exception as e:
            logger.warning(f"[OTP] Échec de l'envoi SMTP ({e}). Le code reste valide et disponible en console.")
            return False

    return True
