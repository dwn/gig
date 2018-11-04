# -*- coding: utf-8 -*-
from app_msg import all_msg
from os import listdir, makedirs, remove
from os.path import join, isdir, splitext, isfile
from time import time, strftime
from base64 import b64encode, b64decode
from hashlib import sha1
from shutil import copytree, rmtree
from fnmatch import fnmatch
from flask import Flask, request, session, g, redirect, abort, render_template, flash, send_from_directory, jsonify
from flask_mail import Mail, Message
from flask_sslify import SSLify
from Crypto import Random
from Crypto.Cipher import AES
from werkzeug.utils import secure_filename
from pymysql import connect
from flask_oauth2_login import GoogleLogin
from json import dumps

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(__name__)
app.config.from_object('config')
mail = Mail(app)
google_login = GoogleLogin(app)
if not app.config['DEBUG']:
  sslify = SSLify(app)

def err(txt):
  flash(txt,'err')

def suc(txt):
  flash(txt,'suc')

def is_allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.teardown_appcontext
def close_db(error):
  if hasattr(g, 'db_cnx'):
    g.db_cnx.close()

def get_db_cursor():
  cnx = getattr(g, 'db_cnx', None)
  if cnx is None:
    cnx = g.db_cnx = connect(database=app.config['DB'], user=app.config['DB_USERNAME'], password=app.config['DB_PASSWORD'], host=app.config['DB_HOST'])
  cur = cnx.cursor() #buffered=True
  return cur

def get_one(str_sql, arr_val=[]):
  cur = get_db_cursor()
  cur.execute(str_sql, arr_val)
  if cur:
    row = cur.fetchone()
    cur.fetchall() #Flush
    return row
  return None

def get_all(str_sql, arr_val=[]):
  cur = get_db_cursor()
  cur.execute(str_sql, arr_val)
  if cur:
    return cur.fetchall()
  return None

def set_db(str_sql, arr_val=[]):
  cur = get_db_cursor()
  rows = cur.execute(str_sql, arr_val)
  g.db_cnx.commit()
  return rows

def get_arr_flag(email):
  row = get_one('select flag from usr where email = %s', [email])
  if row:
    flag = row[0]
    return (flag.split(',') if flag else [])
  return None

def get_lng(email):
  row = get_one('select lng from usr where email = %s', [email])
  if row:
    return row[0]
  return 'en'

def set_fnt(lng):
  session['fnt'] = ('cyrillic' if lng == 'ru' else 'roman')
  return None

def get_all_msg(email):
  return all_msg(get_lng(email))

def get_all_msg_from_session():
  try:
    ret = session['lng']
  except: #session['lng'] does not exist
    ret = 'en'
  return all_msg(ret)

def param_str():
  return ('?disable_cache=%d' % int(time()) if app.config['DISABLE_CACHE'] else '')

def render_template_0(url): #Uses session to determine language
  return render_template(url, app_name=app.config['APP_NAME'], m=get_all_msg_from_session(), google_login_id=app.config['GOOGLE_LOGIN_CLIENT_ID'], google_auth_url=google_login.authorization_url(), p=param_str())

def render_template_1(url, email): #Uses logged-in email to determine language
  return render_template(url, m=get_all_msg(email), google_login_id=app.config['GOOGLE_LOGIN_CLIENT_ID'], p=param_str())

def encrypt(raw):
  bs = AES.block_size
  pad = lambda s: s + (bs - len(s.encode('utf8')) % bs) * chr(bs - len(s.encode('utf8')) % bs)
  raw = pad(raw)
  iv = Random.new().read(AES.block_size)
  cipher = AES.new('this-here-is-key', AES.MODE_CBC, iv)
  return b64encode(iv + cipher.encrypt(raw)).replace('/','_')

def decrypt(enc):
  enc = b64decode(enc.replace('_','/'))
  unpad = lambda s : s.decode('utf8')[0:-ord(s.decode('utf8')[-1])]
  cipher = AES.new('this-here-is-key', AES.MODE_CBC, enc[:16])
  return unpad(cipher.decrypt(enc[16:]))

# SCHEDULE ###################################################################

def date_handler(obj):
  return obj.isoformat() if hasattr(obj, 'isoformat') else obj

def sql_template(type, sql, params=None):
  cur = get_db_cursor()
  try:
    #insert, update, delete
    if type == 3:
      rows = set_db(sql, params)
      return rows
    else:
      #1=fetchall() 2=fetchone()
      with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql, params)
        if type == 1:
          return cursor.fetchall()
        elif type == 2:
          return cursor.fetchone()
  except:
    pass

def get_scheduler(searchDate):
  if not parameter_checker(searchDate):
    return dumps({})
  sql = 'select id, title, arr_usr_id, start, end, if(allDay = %s,true,false) allDay from sch where to_days(start) >= to_days(%s) and to_days(end) <= to_days(%s)'
  params = ('Y', searchDate['start'], searchDate['end'])
  return dumps(sql_template(1, sql, params), default=date_handler);

def set_scheduler(schedule):
  if not parameter_checker(schedule):
    return dumps({'rows' : 0})
  else:
    sql = 'insert into sch(title, arr_usr_id, start, end, allDay) values (%s, %s, %s, %s, %s)'
    params = (schedule['title'], '1', schedule['start'], schedule['end'], schedule['allDay'])
    return dumps({'rows' : sql_template(3, sql, params)})

def del_scheduler(id):
  if not parameter_checker(id):
    return dumps({'rows' : 0})
  else:
    sql = 'delete from sch where id = %s'
    params = (id)
    return dumps({'rows' : sql_template(3, sql, params)})

def put_scheduler(schedule):
  if not parameter_checker(schedule):
    return dumps({'rows' : 0})
  else:
    sql = 'update sch set title = %s, arr_usr_id = %s, start = %s, end = %s, allDay = %s where id = %s'
    params = (schedule['title'], '1', schedule['start'], schedule['end'], schedule['allDay'], schedule['id'])
    return dumps({'rows' : sql_template(3, sql, params)})

def parameter_checker(params):
  if not bool(params):
    return False
  elif hasattr(params,'strip') and not bool(params.strip()):
      return False
  elif hasattr(params,'values'):
    for value in params.values():
      if not parameter_checker(value):
        return False
    return True
  else:
    return True

@app.route('/calendar')
def calendar():
  return render_template('calendar.html')

@app.route('/scheduler', methods=['GET', 'POST', 'PUT', 'DELETE'])
def scheduler():
  if request.method == 'GET':
    start = request.args.get('start')
    end = request.args.get('end')
    return get_scheduler({'start':start , 'end':end})
  if request.method == 'POST':
    start = request.form['start']
    end = request.form['end']
    title = request.form['title']
    allDay = request.form['allDay']
    schedule = {'title':title, 'start':start, 'end':end, 'allDay':allDay}
    return  set_scheduler(schedule)
  if request.method == 'DELETE':
    id = request.form['id']
    return  del_scheduler(id)
  if request.method == 'PUT':
    schedule = request.form
    return put_scheduler(schedule)

##############################################################################

@google_login.login_success
def login_success(token, profile):
  session['logged_in'] = True
  return redirect('main')
  # return jsonify(token=token, profile=profile)

@google_login.login_failure
def login_failure(e):
  return jsonify(error=str(e))

def avatar_path(email):
  pth_fdr = join(app.config['STATIC_FOLDER'],email)
  for filename in listdir(pth_fdr):
    if fnmatch(filename, 'avatar.*'):
      return join(pth_fdr,filename)
  return None

def delete_avatar(email):
  pth_fdr = join(app.config['STATIC_FOLDER'],email)
  for filename in listdir(pth_fdr):
    if fnmatch(filename, 'avatar.*'):
      remove(join(pth_fdr,filename))
  return None

@app.route('/log_in', methods=['GET', 'POST'])
def log_in():
  if request.method == 'POST':
    if session['logged_in']:
      session['email'] = request.form['email']
      row = get_one('select name,lng from usr where email = %s', [session['email']])
      session['name'] = row[0]
      try:
        set_db('update usr set lng = %s where email = %s', [session['lng'],session['email']])
      except: #session['lng'] does not exist
        session['lng'] = row[1]
      # suc('logged in')
      return redirect('')
    else:
      err('invalid email or password')
  return render_template_0('account/log_in.html')

@app.route('/log_out')
def log_out():
  session.pop('logged_in', None)
  suc('logged out')
  return redirect('')

@app.route('/help')
def help():
  return render_template_0('account/help.html')

@app.route('/how_it_works')
def how_it_works():
  return render_template_0('account/how_it_works.html')

@app.route('/change_name', methods=['GET', 'POST'])
def change_name():
  try:
    email = session['email']
  except:  
    return redirect('')
  if request.method == 'POST':
    session['name'] = request.form['new_name']
    set_db('update usr set name = %s where email = %s', [session['name'],email])
    suc('name changed')
  return render_template_1('account/change_name.html', email)

@app.route('/change_email', methods=['GET', 'POST'])
def change_email():
  try:
    email = session['email']
  except:  
    return redirect('')
  if request.method == 'POST':
    if request.form['new_email'] == request.form['confirm_new_email']:
      set_db('update usr set email = %s where email = %s', [request.form['new_email'],email])
      suc('email changed')
    else:
      err('email addresses do not match')
  return render_template_1('account/change_email.html', email)

@app.route('/language/<lng>')
def language(lng):
  try:
    session['logged_in']
    return redirect('set_lng/' + lng)
  except: #Logged out
    session['lng'] = lng
    return redirect('')

@app.route('/set_lng/<lng>')
def set_lng(lng):
  try:
    email = session['email']
  except:  
    return redirect('')
  session['lng'] = lng
  set_fnt(lng)
  set_db('update usr set lng = %s where email = %s', [lng,email])
  return redirect('change_language')

@app.route('/change_language')
def change_language():
  try:
    session['logged_in']
    try:
      email = session['email']
    except:  
      return redirect('')
    return render_template_1('account/change_language.html', email)
  except: #not logged in
    return redirect('')

@app.route('/<email>/<filename>')
def uploaded_file(email, filename):
  return send_from_directory(join(app.config['UPLOAD_FOLDER'],email), filename)

@app.route('/upload_avatar', methods=['GET', 'POST'])
def upload_avatar():
  try:
    email = session['email']
  except:  
    return redirect('')
  if request.method == 'POST':
    if 'file' not in request.files:
      err('no file selected')
      return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
      err('no file selected')
      return redirect(request.url)
    if file and is_allowed_file(file.filename):
      filename = secure_filename(file.filename)
      pth_fdr = join(app.config['UPLOAD_FOLDER'],email)
      try:
        makedirs(pth_fdr)
      except OSError:
        if not isdir(pth_fdr):
          raise
      basename,ext = splitext(filename)
      filename = 'avatar.' + strftime('%Y%m%d%H%M%S') + ext
      pth = join(pth_fdr,filename)
      delete_avatar(email)
      file.save(pth)
    # file.close()
  return render_template('account/upload_avatar.html', pth=avatar_path(email), m=get_all_msg(email), google_login_id=app.config['GOOGLE_LOGIN_CLIENT_ID'], p=param_str())

@app.route('/toggle_flag/<flag>')
def toggle_flag(flag):
  arr_flag = get_arr_flag(session['email'])
  str_arr_flag = ''
  if flag in arr_flag:
    arr_flag.remove(flag)
    str_arr_flag = ','.join(arr_flag)
  else:
    arr_flag += [flag]
    str_arr_flag = ','.join(arr_flag)
  set_db('update usr set flag = %s where email = %s', [str_arr_flag,session['email']])
  return redirect('choose_flag#flag-display')

@app.route('/choose_flag')
def choose_flag():
  try:
    email = session['email']
  except:
    return redirect('')
  return render_template('account/choose_flag.html', all_flag=sorted(listdir(join(app.config['STATIC_FOLDER'],'flag'))), arr_flag=get_arr_flag(email), m=get_all_msg(email), google_login_id=app.config['GOOGLE_LOGIN_CLIENT_ID'], p=param_str())

@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
  try:
    email = session['email']
  except:  
    return redirect('')
  if request.method == 'POST':
    if get_all_msg(email)['type these words: delete this account'].split(':')[1][1:] == request.form['type_these_words_delete_this_account']:
      set_db('delete from usr where email = %s', [email])
      pth_fdr = join(app.config['STATIC_FOLDER'],email)
      rmtree(pth_fdr, ignore_errors=True)
      suc('account deleted')
      return redirect('log_out')
    else:
      err('text incorrect')      
  return render_template_1('account/delete_account.html', email)  

@app.route('/clear')
def clear():
  session.clear()
  session['cleared'] = True
  return redirect('main')

@app.route('/')
def index():
  lng_guess=request.headers['Accept-Language'].split(';')[0].split(',')[0].split('-')[0]
  if not lng_guess:
    lng_guess='en'
  print request.headers['Host']
  try:
    set_fnt(session['lng'])
  except: #session['lng'] does not exist
    set_fnt(lng_guess)
    session['lng'] = lng_guess
  print 'SES',
  for key in session:
    print key, session[key], '|',
  print
  print 'USR',
  try:
    row = get_one('select rowid,* from usr where email = %s', [session['email']])
    for key in row:
      print key, '|',
  except:
    pass
  print
  return render_template('index.html')

@app.route('/main', methods=['GET', 'POST'])
def main():
  email = 'danwnielsen@gmail.com'
  # try:
  #   email = session['email']
  # except:  
  #   return redirect('')
  return render_template('main.html', app_name = app.config['APP_NAME'], m=get_all_msg(email), google_login_id=app.config['GOOGLE_LOGIN_CLIENT_ID'], p=param_str())

@app.errorhandler(500)
def internal_error(error):
  try:
    session['cleared']   
    session.pop('cleared', None)
    return 'An error occurred! The administrator has been informed'
  except: #Clear session and try again
    return redirect('clear')

if __name__ == '__main__':
  if not app.config['DEBUG']:
    import logging
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler(
                     mailhost=(app.config['MAIL_SERVER'],25),
                     fromaddr=app.config['MAIL_DEFAULT_SENDER'],
                     toaddrs=[app.config['ADMIN_EMAIL']],subject='error',
                     credentials=(app.config['MAIL_USERNAME'],app.config['MAIL_PASSWORD']))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
  app.run()
