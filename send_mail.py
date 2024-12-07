import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path=".env", override=True)

def send_email(recipient_email, subject, body):
    try:
        # Load credentials from environment variables
        sender_email = os.getenv('MAIL_USERNAME')
        sender_password = os.getenv('MAIL_PASSWORD')
=
        if not sender_email or not sender_password:
            raise ValueError("Email credentials not found in .env file.")

        # Set up the email parameters
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade connection to secure encrypted SSL/TLS
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
    finally:
        server.quit()

# Example usage
if __name__ == "__main__":
    recipient_email = "mamarih1@gmail.com"
    subject = "Test Email with .env"
    body = "Hello, this is a test email sent using Python with secure credentials!"

    send_email(recipient_email, subject, body)
