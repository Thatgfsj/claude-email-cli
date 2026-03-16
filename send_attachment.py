import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.policy import SMTP
import json

# Read config
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Email settings
smtp_host = config['smtp']['host']
smtp_port = config['smtp']['port']
smtp_user = config['smtp']['username']
smtp_password = config['smtp']['password']

# Email content
from_email = smtp_user
to_email = "18738022016@126.com"
subject = "教资科一作文 - 言传身教，润物无声"
body = """您好！

这是您要求的教资科一综合素质作文，题目是"言传身教，润物无声"，议论文格式，不少于800字。

请查收附件。

祝好！
"""

# Create message with SMTP policy for proper encoding
msg = MIMEMultipart(policy=SMTP)
msg['From'] = from_email
msg['To'] = to_email
msg['Subject'] = subject
msg.attach(MIMEText(body, 'plain', 'utf-8'))

# Attach file
attachment_path = "I:/.claude email/作文_言传身教.docx"
attachment_name = "作文_言传身教.docx"

with open(attachment_path, 'rb') as attachment:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        'attachment',
        filename=('utf-8', '', attachment_name)
    )
    msg.attach(part)

# Send email
print(f"Connecting to {smtp_host}:{smtp_port}...")
server = smtplib.SMTP_SSL(smtp_host, smtp_port)
server.login(smtp_user, smtp_password)
print(f"Sending email to {to_email}...")
server.sendmail(from_email, to_email, msg.as_string())
server.quit()
print("Email sent successfully!")
