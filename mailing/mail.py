from __future__ import print_function
from mailing import auth
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase
import base64
from apiclient import discovery
import httplib2

SCOPES = ['https://mail.google.com/']
MY_ADDRESS = "hey@heybooster.ai"
SERVERNAME = "heybooster"
BOTNAME = "HeyBooster Alert Bot"
SCOPES = ['https://mail.google.com/']

CLIENT_SECRET_FILE = 'client_id.json'


def mail(text, STATUS, filename=None):
    """
    STATUS: INFO, ERROR
    text: Message to be sent
    """
    # For each contact, send the email:
    msg = MIMEMultipart()  # create a message
    # add in the actual person name to the message template
    # Prints out the message body for our sake
    # setup the parameters of the message
    msg['From'] = MY_ADDRESS
    recipients = ["ali@heybooster.ai"]
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = "{}-{}-{}".format(BOTNAME, SERVERNAME, STATUS)
    msg.attach(MIMEText(text, 'plain'))
    if filename:
        with open(filename, "rb") as attachment:
            # Add file as application/octet-stream
            # Email client can usually download this automatically as attachment
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        # Encode file in ASCII characters to send by email
        encoders.encode_base64(part)
        # Add header as key/value pair to attachment part
        part.add_header(
            "Content-Disposition",
            "attachment; filename= {}".format(filename)
        )
        msg.attach(part)
    message = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    try:
        message = gmail_service.users().messages().send(userId='me', body=message).execute()
        print('Message Id: %s' % message['id'])
        return message
    except Exception as error:
        print('A mail error occurred: %s' % error)


if __name__ == '__main__':
    authInst = auth.auth(SCOPES, CLIENT_SECRET_FILE, BOTNAME)
    credentials = authInst.get_credentials()
    http = credentials.authorize(httplib2.Http())
    gmail_service = discovery.build('gmail', 'v1', http=http)
    message = " Server has finished.\nINFO:\n{}\n"
    intro_string = ("Hi,\n{} in {}" + message.format(BOTNAME, SERVERNAME, message))
    mail(intro_string, 'INFO')
