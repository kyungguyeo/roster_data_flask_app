from flask import Flask, render_template, request
import pandas as pd
import os
from clean_roster import data_check, summarize
import json
import dropbox

UPLOAD_FOLDER = "~/uploads/"
ALLOWED_EXTENSIONS = set(['csv'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method=='POST':
        f = request.files['file']
        roster_df = pd.read_csv(f.stream)
        path_noext = os.path.splitext(f.filename)[0]
        f_name = os.path.basename(path_noext)
        clean_name = f_name + '_clean.csv'
        summ_name = f_name + '_summary.csv'
        issues, roster_df = data_check(roster_df,False)
        if any(issues.values()):
            return render_template('no_good.html', feedback = issues)
        else:
            return render_template('success.html', email_func = dbx)

@app.route('/dbx', methods = ['GET', 'POST'])
def dbx(): #drops to /Apps/RosterData/roster_data_drop
    db = dropbox.Dropbox('PSGsZQnzMeAAAAAAAAAAtS5tk1W57GHwbVp0ycdbF7wXTKXFlal3hTdstseeKNay')
    for file in os.listdir(os.getcwd()):
        if ("_clean.csv" in file) or ("_summary.csv" in file):
            with open(file, "rb") as f:
                db.files_upload(f.read(), '/roster_data_drop/' + f.name, mute = True)
    return render_template('dropbox.html')

@app.route('/dwnld', methods = ['GET'])
def dwnld(): #downloads _summary file to cur dir

if __name__ == '__main__':
    app.run(debug = True)