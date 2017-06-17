from flask import Flask, render_template, request
from werkzeug import secure_filename
import pandas as pd
import os
from clean_roster import clean
from io import StringIO
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
import json
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method=='POST':
        f = request.files['file']
        roster = pd.read_csv(f.stream)
        path_noext = os.path.splitext(f.filename)[0]
        f_name = os.path.basename(path_noext)
        clean_name = f_name + '_clean.csv'
        summ_name = f_name + '_summary.csv'
        message = clean(roster,False,clean_name,summ_name,False)
        if message:
            return render_template('no_good.html', feedback = message)
        else:
            return render_template('success.html', email_func = email_youthtruth)
@app.route('/email', methods = ['GET', 'POST'])
def email_youthtruth():
    ##Attach Email
    email_data = json.loads(open('/Users/johnnyyeo/.credentials/email_creds.json').read())
    fromaddr = email_data['user']
    toaddr = ['johnnyy@youthtruthsurvey.org']
    for file in os.listdir(os.getcwd()):
        if ('.csv' in file) and ('_clean' in file):
            clean_file = file
        elif ('.csv' in file) and ('_summary' in file):
            summary_file = file
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = ", ".join(toaddr)
    msg['Subject'] = "New Roster Data!"
    body = """
        <html>
            <head></head>
            <body>
                Ahoy! New Roster Data For you!
            </body>
        </html>
        """
    msg.attach(MIMEText(body, 'html'))
    attachment = open(clean_file, 'rb')
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename = %s" % clean_file)
    msg.attach(part)

    attachment = open(summary_file, 'rb')
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename = %s" % summary_file)
    msg.attach(part)

    ##Send Email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, email_data['pass'])
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

    return render_template('email.html')

if __name__ == '__main__':
    app.run(debug = True)