#!/usr/bin/env python
'''
hawthorne_server.py
data entry management
'''
import datetime
from functools import wraps
import os

import boto
import flask
from flaskext.bcrypt import Bcrypt
from mongoengine import *


app = flask.Flask(__name__)
app.config.from_envvar('HAWTHORNE_SETTINGS')
bcrypt = Bcrypt(app)

# initialize the mongoengine connection
connect(app.config['MONGO_CONFIG']['db_name']
    , host=app.config['MONGO_CONFIG']['host']
    , port=int(app.config['MONGO_CONFIG']['port']))


''' decorators
'''
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in flask.session:
            return flask.redirect(flask.url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def verification_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # check that someone is logged in
        if 'email' not in flask.session:
            return flask.redirect(flask.url_for('login'))
        # check verification
        user = User.objects(email=flask.session['email'])[0]
        if not user.verified:
            return flask.redirect(flask.url_for('verification_status'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # check that someone is logged in
        if 'email' not in flask.session:
            return flask.abort(404)
        # check admin status
        user = User.objects(email=flask.session['email'])[0]
        if not user.admin_rights:
            return flask.redirect(flask.url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


''' routes
'''
@app.route('/')
def home():
    return flask.render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
# redirect-if-logged-in decorator
def register():
    ''' displays registration page
    sends confirmation email to registrant
    sends notification email to admin
    '''
    if flask.request.method == 'GET':
        return flask.render_template('register.html')

    elif flask.request.method == 'POST':
        # check that passwords match
        if flask.request.form['password'] != \
            flask.request.form['retype_password']:
            return flask.render_template('register.html'
                    , error='Your submitted passwords did not match.')

        # check that user email is unique
        duplicates = User.objects(email=flask.request.form['email'])
        if duplicates:
            return flask.render_template('register.html'
                , error='This email address is already registered.')

        # create the new user
        try:
            new_user = User(
                admin_rights = False
                , api_id = 'ID' + _generate_random_string(32)
                , api_key = _generate_random_string(34)
                , email = flask.request.form['email']
                , email_confirmation_code = _generate_random_string(34)
                , email_confirmed = False
                , last_login_time = datetime.datetime.utcnow()
                , name = flask.request.form['name']
                , organization = flask.request.form['organization']
                , password_hash = bcrypt.generate_password_hash(
                    flask.request.form['password'])
                , registration_time = datetime.datetime.utcnow()
                , verified = False
                , verified_by = None)
            new_user.save() 
        except:
            return flask.render_template('register.html'
                , error='There was an error in the form, sorry.')
        
        # seek email confirmation
        _send_confirmation_email(new_user)

        # log the user in  
        flask.session['email'] = user.email

        # redirect to a holding area
        return flask.redirect(flask.url_for('verification_status'))


@app.route('/confirm_email/<code>')
def confirm_email(code):
    ''' click this link to confirm your email
    '''
    user = User.objects(email_confirmation_code=code)
    if not user:
        return flask.redirect(flask.url_for('home'))
    # save their email confirmation status
    user = user[0]
    user.email_confirmed = True

    # log the user in (controversy!)
    user.last_login_time = datetime.datetime.utcnow()
    user.save()
    flask.session['email'] = user.email

    # email an admin for verification
    _send_admin_verification(user)
        
    # redirect to a holding area
    return flask.redirect(flask.url_for('verification_status'))


@app.route('/verification_status')
@login_required
def verification_status():
    ''' shows verification status
    '''
    user = User.objects(email=flask.session['email'])[0]
    # if verified/confirmed, redirect to dash
    return flask.render_template(
        'verification_status.html'
        , email_confirmed=user.email_confirmed
        , identity_verified=user.verified)


@app.route('/login', methods=['GET', 'POST'])
# redirect-if-logged-in decorator
def login():
    ''' displays standalone login page
    handles login requests
    '''
    if flask.request.method == 'GET':
        return flask.render_template('login.html')

    elif flask.request.method == 'POST':
        # find the user by their email
        user = User.objects(email=flask.request.form['email'])
        if not user:
            return flask.render_template('login.html'
                , error='That\'s not a valid email address or password.')
        
        user = user[0]
        # verify the password 
        if not bcrypt.check_password_hash(user.password_hash
            , flask.request.form['password']):
            return flask.render_template('login.html'
                , error='That\'s not a valid email address or password.')

        # they've made it through the gauntlet, log them in
        user.last_login_time = datetime.datetime.utcnow()
        user.save()
        flask.session['email'] = flask.request.form['email']

        return flask.redirect(flask.url_for('dashboard'))


@app.route('/logout')
def logout():
    ''' blow away the session
    redirect home
    '''
    flask.session.pop('email', None)

    return flask.redirect(flask.url_for('home'))


@app.route('/dashboard')
@verification_required
def dashboard():
    ''' show the dashboard
    '''
    return flask.render_template('dashboard.html')


@app.route('/directory/', defaults={'internal_id': None})
@app.route('/directory/<internal_id>', methods=['GET', 'POST'])
@admin_required
def directory(internal_id):
    ''' show the users and their verification/confirmation status
    if there's an email included in the route, render that profile for editing
    '''
    if flask.request.method == 'POST':
        user = User.objects(id=internal_id)
        if not user:
            flask.abort(404)
        user = user[0]

        user.name = flask.request.form['name']
        user.email = flask.request.form['email']
        user.organization = flask.request.form['organization']

        if flask.request.form['verification'] == 'verified':
            user.verified = True
        elif flask.request.form['verification'] == 'unverified':
            user.verified = False
        
        if flask.request.form['admin'] == 'admin':
            user.admin_rights = True
        elif flask.request.form['admin'] == 'normal':
            user.admin_rights = False

        try:
            user.save()
            message = 'updates saved successfully'
            return flask.render_template('directory_single_user.html'
                , email=user.email, success=message, user=user)
        except:
            return flask.render_template('directory_single_user.html'
                , email=user.email, error='error saving changes, sorry |:'
                , user=user)

        
    if flask.request.method == 'GET':
        if internal_id:
            user = User.objects(id=internal_id)
            if not user:
                flask.abort(404)
            user = user[0]
            return flask.render_template('directory_single_user.html', user=user)

        users = User.objects()
        return flask.render_template('directory.html', users=users)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    ''' viewing/editing ones own profile
    admins can view/edit at /directory
    '''
    return flask.render_template('profile.html')


@app.route('/forgot/', defaults={'code': None})
@app.route('/forgot/<code>')
# logged-in decorator
def forgot(code):
    ''' take input email address
    send password reset link
    '''
    return flask.render_template('forgot.html')


''' mongoengine classes
'''
class User(Document):
    ''' some are admins some are not
    '''
    admin_rights = BooleanField(required=True)
    api_id = StringField()
    api_key = StringField()
    email = EmailField(required=True, unique=True, max_length=254)
    email_confirmation_code = StringField(required=True)
    email_confirmed = BooleanField(required=True)
    last_login_time = DateTimeField(required=True)
    name = StringField()
    organization = StringField(required=True)
    password_hash = StringField(required=True)
    registration_time = DateTimeField(required=True)
    verified = BooleanField(required=True)


''' utility functions
'''
def _generate_random_string(length):
    ''' generating API IDs and keys
    '''
    # technique from: http://stackoverflow.com/questions/2898685
    return ''.join(
        map(lambda x: '0123456789abcdefghijklmnopqrstuvwxyz'[ord(x)%36]
        , os.urandom(length)))
    

def _send_admin_verification(user):
    ''' email to an admin indicating that there a user needs verification
    '''
    body = '''
        Howdy!  Someone new has confirmed his or her email address and now 
        needs to be verified by an admin.  Here are the details:

        Name: %s
        Email: %s
        Organization: %s

        Click the following link to edit the verification status of this
        person.

        http://127.0.0.1:8000/directory/%s

        Thanks!
        ''' % (user.name, user.email, user.organization, user.email)

    # send to the AWS verified sender..should probably use a manager's email
    _send_email(
        app.config['AWS']['verified_sender']
        , 'Hawthorne -- %s needs to be verified' % user.name
        , body)


def _send_confirmation_email(user):
    ''' sends an email to a newly-registered user with a confirmation code
    '''
    body = '''
        Hello, this email was recently used to sign up for an account with 
        Hawthorne.  If it was you that signed up for this account, please click
        the link below to confirm your email address.
        
        If you did not sign up for this account, please disregard this message.

        http://127.0.0.1:8000/confirm_email/%s

        Thanks!
        ''' % user.email_confirmation_code

    _send_email(user.email, 'Hawthorne email confirmation', body)


def _send_email(recipient, subject, body):
    ''' send an email using SES from the config's verified sender
    '''
    connection = boto.connect_ses(
        aws_access_key_id=app.config['AWS']['access_key_id']
        , aws_secret_access_key=app.config['AWS']['secret_access_key'])

    result = connection.send_email(
        app.config['AWS']['verified_sender']
        , subject
        , body
        , [recipient])
    # need to catch errors in result


@app.template_filter('_format_datetime')
def _format_datetime(dt, formatting='medium'):
    ''' jinja filter for displaying datetimes
    usage in the jinja template:
        publication date: {{ article.pub_date|_format_datetime('full') }}
    '''
    if formatting == 'full':
        return dt.strftime('%A %B %d, %Y at %H:%M:%S')
    if formatting == 'medium':
        return dt.strftime('%B %d, %Y at %H:%M:%S')
    if formatting == 'full-day':
        return dt.strftime('%A %B %d, %Y')
    if formatting == 'day-month-year':
        return dt.strftime('%B %d, %Y')
    if formatting == 'hours-minutes-seconds':
        return dt.strftime('%H:%M:%S')

@app.before_request
def csrf_protect():
    ''' CSRF protection via http://flask.pocoo.org/snippets/3/
    '''
    if flask.request.method == 'POST':
        token = flask.session.pop('_csrf_token', None)
        if not token or token != flask.request.form.get('_csrf_token'):
            flask.abort(403)

def _generate_csrf_token():
    if '_csrf_token' not in flask.session:
        flask.session['_csrf_token'] = _generate_random_string(24)
    return flask.session['_csrf_token']

app.jinja_env.globals['csrf_token'] = _generate_csrf_token


''' initialization
'''
def init():
    ''' adds a default admin to the system
    usage:
        $ /path/to/virtualenv/bin/python
        >> from hawthorne_server import init
        >> init()
        user bruce@wayneindustries created with specified password
    '''
    initial_user = app.config['INITIAL_USER']

    try:
        default_admin = User(
            admin_rights = True
            , api_id = 'ID' + _generate_random_string(32)
            , api_key = _generate_random_string(34)
            , email = initial_user['email']
            , email_confirmation_code = _generate_random_string(34)
            , email_confirmed = False
            , last_login_time = datetime.datetime.utcnow()
            , name = initial_user['name']
            , organization = initial_user['organization']
            , password_hash = bcrypt.generate_password_hash(
                initial_user['password'])
            , registration_time = datetime.datetime.utcnow()
            , verified = True
        )

        default_admin.save()
        print 'user %s created with specified password' % default_admin['email']
    except:
        print 'insertion failed; there may be a non-unique field'


if __name__ == '__main__':
    app.run(
        host=app.config['APP_IP']
        , port=app.config['APP_PORT']
    )
