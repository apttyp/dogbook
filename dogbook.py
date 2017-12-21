import os
import uuid
from threading import Thread
from flask import Flask, Response, request, make_response, render_template, session, redirect, url_for, flash, jsonify as flask_jsonify
from flask_script import Manager, Shell
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Required
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_mail import Message, Mail
from getmyip import Getmyip
from helpers import get_headers, get_dict, secure_cookie
# from .helpers import get_headers, status_code, get_dict, get_request_range, check_basic_auth, check_digest_auth, \
#     secure_cookie, H, ROBOT_TXT, ANGRY_ASCII, parse_multi_value_header, next_stale_after_value, \
#     digest_challenge_response
import logging

log_file = "./basic_logger.log"

logging.basicConfig(filename=log_file, level=logging.DEBUG)

ENV_COOKIES = (
    '_gauges_unique',
    '_gauges_unique_year',
    '_gauges_unique_month',
    '_gauges_unique_day',
    '_gauges_unique_hour',
    '__utmz',
    '__utma',
    '__utmb'
)

def jsonify(*args, **kwargs):
    response = flask_jsonify(*args, **kwargs)
    if not response.data.endswith(b'\n'):
        response.data += b'\n'
    return response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI']=\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.163.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
# app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_USERNAME'] = '1811261904@163.com'
app.config['MAIL_PASSWORD'] = 'hehe123'

app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_MAIL_SENDER'] = '1811261904@163.com'

# app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')
app.config['FLASKY_ADMIN'] = 'tonystar@aispeech.com'

# print(app.config['SQLALCHEMY_DATABASE_URI'])
manager = Manager(app)
bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username

class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject, sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            session['known'] = False
            if app.config['FLASKY_ADMIN']:
                send_email(app.config['FLASKY_ADMIN'], 'New User', 'mail/new_user', user=user)
        else:
            session['known'] = True
        session['name'] = form.name.data
        form.name.data = ''
        return redirect(url_for('index'))
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False))

@app.route('/ip')
def original_ip():
    myip = Getmyip()
    localip = myip.getip()
    return render_template('my_ip.html', maybe_ip=localip)

@app.route('/uuid')
def view_uuid():
    return jsonify(uuid=str(uuid.uuid4()))

@app.route('/user-agent')
def view_useragent():
    headers = get_headers()
    return jsonify({'user-agent': headers['user-agent']})



@app.route('/headers')
def view_headers():
    """Returns HTTP HEADERS."""

    return jsonify(get_dict('headers'))

@app.route('/get', methods=('GET',))
def view_get():
    """Returns GET Data."""

    return jsonify(get_dict('url', 'args', 'headers', 'origin'))

@app.route('/cookies')
def view_cookies(hide_env=True):
    """Returns cookie data."""
    # print(request.cookies.items())
    logging.warn(request.cookies.items())
    cookies = dict(request.cookies.items())

    if hide_env and ('show_env' not in request.args):
        for key in ENV_COOKIES:
            try:
                del cookies[key]
            except KeyError:
                pass

    return jsonify(cookies=cookies)

@app.route('/cookies/set/<name>/<value>')
def set_cookie(name, value):
    r = app.make_response(redirect(url_for('view_cookies')))
    r.set_cookie(key=name, value=value, secure=secure_cookie())
    return  r

@app.route('/cookies/set')
def set_cookies():
    """Sets cookie(s) as provided by the query string and redirects to cookie list."""

    cookies = dict(request.args.items())
    r = app.make_response(redirect(url_for('view_cookies')))
    for key, value in cookies.items():
        r.set_cookie(key=key, value=value, secure=secure_cookie())

    return r

@app.route('/delete/cookies')
def delete_cookies():
    cookies = dict(request.args.items())
    r=app.make_response(redirect(url_for('view_cookies')))
    for key, value in cookies.items():
        r.delete_cookie(key=key)

    return r

@app.route('/xml')
def view_xml():
    # return render_template('sample.xml')
    response = make_response(render_template('sample.xml'))
    response.headers['Content-Type'] = "application/xml"
    return  response

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def inter_server_error(e):
    return render_template('500.html'), 500

@app.route('/user/<code>')
def user(code):
    return render_template('user.html', code=code)

@app.route('/html')
def view_my_html():
    return render_template('my_html.html')

@app.route('/encoding/utf8')
def encoding():
    return render_template('utf8.txt')

@app.route('/image/png')
def image_png():
    mydata = myread_file('image/pig_icon.png')
    return Response(mydata, headers={'Content-Type': 'image/png'})

@app.route('/image/jpg')
def image_jpg():
    mydata = myread_file('image/jackal.jpg')
    return Response(mydata, headers={'Content-Type': 'image/jpg'})

@app.route('/image/svg')
def image_svg():
    mydata = myread_file('image/svg_logo.svg')
    return Response(mydata, headers={'Content-Type': 'image/svg'})

@app.route('/image/webp')
def image_webp():
    mydata = myread_file('image/wolf_1.webp')
    return Response(mydata, headers={'Content-Type': 'image/webp'})

def myread_file(filename):
    filepath = os.path.join(tmpl_dir, filename)
    return open(filepath, 'rb').read()


if __name__ == '__main__':
    manager.run()
