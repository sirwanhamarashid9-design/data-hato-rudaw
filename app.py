from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, datetime

BASE=os.path.dirname(__file__); DB=os.path.join(BASE,'database.db'); UP=os.path.join(BASE,'uploads')
os.makedirs(UP,exist_ok=True)
app=Flask(__name__); app.secret_key=os.environ.get('SECRET_KEY','CHANGE_THIS_SECRET_KEY')
SECTIONS=['مقر قيادة الفرقة','فصيل الحماية','مشاور القانوني','قسم IT','قسم اعلام','قسم الادارة','قسم الاستخبارات','قسم الميرة','قسم الاتصالات','قسم التدريب','قسم الحسابات','سرية مقرو الخدمات','سرية دفاع والواجبات','سرية الانضباط العسكريه','وهدة الميدان الطبية','فوج المغاوير','كتيبة مقاومة الطائرات','كتيبة مقاتلة الدروع','كتيبة الاشغال والهندسة العسكريه']

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
 c=db(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT,section_id INTEGER); CREATE TABLE IF NOT EXISTS sections(id INTEGER PRIMARY KEY,name TEXT UNIQUE); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,section_id INTEGER,event_date TEXT,server_time TEXT,event_type TEXT,rank TEXT,full_name TEXT,notes TEXT,attachment TEXT,status TEXT DEFAULT 'normal',created_by INTEGER); CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);''')
 if not c.execute("select id from users where username='admin'").fetchone(): c.execute('insert into users(username,password,role) values(?,?,?)',('admin',generate_password_hash('Admin@123'),'super'))
 if not c.execute('select id from sections limit 1').fetchone(): c.executemany('insert into sections(name) values(?)',[(x,) for x in SECTIONS])
 for k,v in [('start_time','08:00'),('end_time','12:00')]: c.execute('insert or ignore into settings(k,v) values(?,?)',(k,v))
 c.commit(); c.close()

def current(): return db().execute('select * from users where id=?',(session['uid'],)).fetchone() if session.get('uid') else None
@app.context_processor
def ctx():
 c=db(); return {'me':current(),'sections':c.execute('select * from sections order by id').fetchall(),'start':c.execute("select v from settings where k='start_time'").fetchone()['v'],'end':c.execute("select v from settings where k='end_time'").fetchone()['v']}
@app.route('/',methods=['GET','POST'])
def login():
 if request.method=='POST':
  c=db(); u=c.execute('select * from users where username=?',(request.form['username'],)).fetchone()
  if u and check_password_hash(u['password'],request.form['password']): session['uid']=u['id']; return redirect(url_for('dashboard'))
  flash('ناوی بەکارهێنەر یان وشەی نهێنی هەڵەیە')
 return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect('/')
@app.route('/dashboard')
def dashboard():
 if not current(): return redirect('/')
 c=db(); me=current(); q='select e.*,s.name section_name from events e join sections s on s.id=e.section_id'; args=[]
 if me['role']=='section': q+=' where e.section_id=?'; args.append(me['section_id'])
 q+=' order by e.id desc'; events=c.execute(q,args).fetchall(); return render_template('dashboard.html',events=events)
@app.route('/event',methods=['POST'])
def event():
 me=current(); c=db(); sid=int(request.form['section_id']) if me['role']=='super' else me['section_id']; now=datetime.datetime.now(); st= c.execute("select v from settings where k='start_time'").fetchone()['v']; en=c.execute("select v from settings where k='end_time'").fetchone()['v']; tm=now.strftime('%H:%M'); status='normal' if st<=tm<=en else 'late'
 f=request.files.get('attachment'); fn=None
 if f and f.filename: fn=f"{now.strftime('%Y%m%d%H%M%S')}_{secure_filename(f.filename)}"; f.save(os.path.join(UP,fn))
 c.execute('insert into events(section_id,event_date,server_time,event_type,rank,full_name,notes,attachment,status,created_by) values(?,?,?,?,?,?,?,?,?,?)',(sid,request.form['event_date'],now.strftime('%Y-%m-%d %H:%M:%S'),request.form['event_type'],request.form['rank'],request.form['full_name'],request.form['notes'],fn,status,me['id'])); c.commit(); return redirect(url_for('dashboard'))
@app.route('/delete/<int:eid>')
def delete(eid):
 me=current(); c=db(); e=c.execute('select * from events where id=?',(eid,)).fetchone()
 if e and (me['role']=='super' or e['section_id']==me['section_id']): c.execute('delete from events where id=?',(eid,)); c.commit()
 return redirect(url_for('dashboard'))
@app.route('/admin',methods=['GET','POST'])
def admin():
 me=current();
 if not me or me['role']!='super': return redirect(url_for('dashboard'))
 c=db()
 if request.method=='POST':
  action=request.form['action']
  if action=='user': c.execute('insert into users(username,password,role,section_id) values(?,?,?,?)',(request.form['username'],generate_password_hash(request.form['password']),'section',request.form['section_id']))
  elif action=='section': c.execute('insert into sections(name) values(?)',(request.form['name'],))
  elif action=='settings': c.execute("update settings set v=? where k='start_time'",(request.form['start_time'],)); c.execute("update settings set v=? where k='end_time'",(request.form['end_time'],))
  c.commit(); return redirect(url_for('admin'))
 return render_template('admin.html',users=c.execute("select u.*,s.name section_name from users u left join sections s on s.id=u.section_id where u.role='section'").fetchall())
@app.route('/download/<fn>')
def download(fn): return send_from_directory(UP,fn,as_attachment=True)
@app.route('/export')
def export():
 import csv, io
 me=current(); c=db(); q='select e.id,s.name,e.event_date,e.server_time,e.event_type,e.rank,e.full_name,e.notes,e.status from events e join sections s on s.id=e.section_id'; args=[]
 if me['role']=='section': q+=' where e.section_id=?'; args=[me['section_id']]
 rows=c.execute(q,args).fetchall(); out=io.StringIO(); w=csv.writer(out); w.writerow(['ID','Section','Event date','Server time','Type','Rank','Full name','Notes','Status']); [w.writerow(tuple(r)) for r in rows]; return app.response_class('\ufeff'+out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=events.csv'})
init()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
