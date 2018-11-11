# -*- coding: utf-8 -*-
from os.path import join, isfile
from flask import Flask, request, session, redirect, render_template, flash
from flask_htpasswd import HtPasswdAuth
from flask_mail import Mail, Message
from flask_sslify import SSLify
from werkzeug.utils import secure_filename
from time import time, sleep
import json
import sendgrid
from sendgrid.helpers.mail import *
import os
import datetime
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(__name__)
app.config.from_pyfile('../config_simple-mailer.py')
mail = Mail(app)
if not app.config['DEBUG']:
  sslify = SSLify(app)
htpasswd = HtPasswdAuth(app)

def err(txt):
  flash(txt,'err')

def suc(txt):
  flash(txt,'suc')

def log(txt):
  app.logger.info(txt)
  f = open('log.txt', 'a')
  f.write(txt)
  f.close()
  
@app.teardown_appcontext
def close(error):
  return None

def send_email(row, from_email, subject, text, sendgrid_api_key):
  subject2 = subject.replace('SURNAME',row[0]).replace('NAME',row[1]).replace('EMAIL',row[2]).replace('SCHOOL',row[3])
  text2 = text.replace('SURNAME',row[0]).replace('NAME',row[1]).replace('EMAIL',row[2]).replace('SCHOOL',row[3])
  sg = sendgrid.SendGridAPIClient(apikey=sendgrid_api_key)
  from_email = Email(from_email)
  to_email = Email(row[2])
  content = Content("text/plain", text2)
  mail = Mail(from_email, subject2, to_email, content)
  response = sg.client.mail.send.post(request_body=mail.get())
  return response

def csv_file_to_list(f):
  return list(filter(None,map(str.strip, f.read().replace('\r','\n').replace(',','\n').replace('\n\n','\n').replace('\n\n','\n').split('\n'))))

@app.route('/show_log')
def show_log():
  open('log.txt', 'a').close() # Touch file
  f = open('log.txt', 'r')
  txt = f.read()
  f.close()
  return render_template('show_log.html',txt=txt)

@app.route('/send_batch')
def send_batch():
  # print session
  # Begin batch email
  for i in range (session['num_entries']):
    send_email(session['arr_s'][4*i:4*(i+1)], session['from_email'], session['subject'], session['email_body'], session['sendgrid_api_key'])
  suc('email messages sent')
  log('SUCCESS')
  dummy_row = ['', '', app.config['FINAL_REPORT_EMAIL'], '']
  send_email(dummy_row, session['from_email'], 'Simple Mailer', 'Total emails sent: %d' % session['num_entries'], session['sendgrid_api_key'])
  return redirect('/')

@app.route('/test')
def test():
  log('<br>%s  %s  %d  ' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), session['mailing_name'], session['num_entries']))
  return render_template('test.html', id=session['mail_tester_username'], tm=session['tm'])

@app.route('/mms', methods=['GET', 'POST'])
def mms():
  return render_template('mms.html')

@app.route('/', methods=['GET', 'POST'])
@htpasswd.required
def index(user):
  if request.method == 'GET':
    # In case you want to add another language
    # lng_guess=request.headers['Accept-Language'].split(';')[0].split(',')[0].split('-')[0]
    # if not lng_guess:
    #   lng_guess='en'
    # print request.headers['Host']    
    return render_template('index.html')
  if request.method == 'POST':
    try:
      session['mail_tester_username'] = request.form['mail_tester_username']
      session['mailing_name'] = request.form['mailing_name']
      session['from_email'] = request.form['from_email']
      session['subject'] = request.form['subject']
      session['sendgrid_api_key'] = request.form['sendgrid_api_key']
      session['email_body'] = request.form['email_body']
    except:
      pass
    try: # Send button
      # Check file
      if 'file' not in request.files:
        err('no file part (check API key and file selection)')
        return redirect(request.url)
      file = request.files['file']
      if file.filename == '':
        err('no selected file')
        return redirect(request.url)
      if file: # and allowed_file(file.filename): # In case you want to check file extension
        filename = secure_filename(file.filename)
        session['filepath'] = join(app.config['UPLOAD_FOLDER'], filename)
        file.save(session['filepath'])
        f = open(session['filepath'], 'r')
        # Check data validity
        arr_s = csv_file_to_list(f)
        print arr_s
        error = False
        if (len(arr_s) % 4) != 0: # Data comes in fours
          error = True
        num_entries = len(arr_s) // 4
        for i in range(num_entries): # Email addresses contain @
          if '@' not in arr_s[4*i+2]:
            error = True
        if error == True:
          err('file corrupt')
          return redirect(request.url)
        else:
          suc('file uploaded: ' + str(num_entries) + (' entry' if num_entries==1 else ' entries'))
        f.close()
      # File valid
      f = open(session['filepath'], 'r') # Input file
      session['arr_s'] = csv_file_to_list(f)
      session['num_entries'] = len(session['arr_s']) // 4
      # Test mail to see if it looks like spam
      session['tm'] = int(time())
      dummy_row = ['', '', session['mail_tester_username'] + '-' + str(session['tm']) + '@mail-tester.com', '']
      response = send_email(dummy_row, session['from_email'], session['subject'], session['email_body'], session['sendgrid_api_key'])
      session.pop('filepath')
      return redirect('/test')
    except:
      return redirect('/')

if __name__ == '__main__':
  if not app.config['DEBUG']:
    import logging
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler(
      mailhost=(app.config['ERROR_MAIL_SERVER'],25),
      fromaddr=app.config['ERROR_MAIL_DEFAULT_SENDER'],
      toaddrs=[app.config['ADMIN_EMAIL']],subject='error',
      credentials=(app.config['ERROR_MAIL_USERNAME'],app.config['ERROR_MAIL_PASSWORD']))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
  app.run()
