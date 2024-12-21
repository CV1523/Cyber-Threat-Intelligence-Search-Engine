import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def makeCampaign():

    excel_file = 'contacts.csv'
    df = pd.read_csv(excel_file)

    contacts = df['Emails'].dropna().tolist()

    print(contacts)

    with open('./email/templates/toPush/index.html', 'r') as file:
        html_content = file.read()

    print("\n Campaign Initialized")

    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['Subject'] = 'Campaign Test'

    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            
            # msg['To'] = contact
            msg['Bcc'] = ', '.join(contacts)
            server.send_message(msg)

            print("\n Alert Sent!")

    except Exception as e:
        print(f'Error: {e}')

    return True

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
