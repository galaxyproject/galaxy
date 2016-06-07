#!/usr/bin/env python

"""
Server for realtime Galaxy communication.


At first you need to install a few requirements.

. GALAXY_ROOT/.venv/bin/activate    # activate Galaxy's virtualenv
pip install flask flask-login flask-socketio eventlet   # install the requirements



As a next step start the communication server with something like this:

./scripts/communication_server.py --port 7070 --host localhost

Please make sure the host and the port matches the ones on config/galaxy.ini

The communication server feature of Galaxy can be controlled on three different levels:
  1. Admin can activate/deactivate communication (config/galaxy.ini)
  2. User can actrivate/deactivate for one session (in the communication window)
  3. User can actrivate/deactivate as personal-setting for ever (Galaxy user preferences)


"""
import argparse
import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from flask import Flask, request, make_response, current_app
from flask_socketio import SocketIO, emit, disconnect, join_room, leave_room, close_room, rooms
import flask.ext.login as flask_login
from flask.ext.login import current_user
from datetime import timedelta
from functools import update_wrapper

import galaxy.config
from galaxy.model.orm.scripts import get_config
from galaxy.model import mapping
from galaxy.util.properties import load_app_properties
from galaxy.web.security import SecurityHelper

# Get config file and load up SA session
config = get_config( sys.argv )
model = mapping.init( '/tmp/', config['db_url'] )
sa_session = model.context.current

# With the config file we can load the full app properties
app_properties = load_app_properties(ini_file=config['config_file'])
# We need the ID secret for configuring the security helper to decrypt
# galaxysession cookies.
security_helper = SecurityHelper(id_secret=app_properties['id_secret'])
# And get access to the models
# Login manager to manager current_user functionality
login_manager = flask_login.LoginManager()

app = Flask(__name__)
app.config['SECRET_KEY'] = app_properties['id_secret']
login_manager.init_app(app)
socketio = SocketIO(app)

@login_manager.request_loader
def findUserByCookie(request):
    cookie_value = request.cookies.get('galaxysession')
    if not cookie_value:
        return

    session_key = security_helper.decode_guid(cookie_value)
    user_session = sa_session.query(model.GalaxySession) \
            .filter_by(session_key=session_key, is_valid=True).first()
    return user_session.user

# Taken from flask.pocoo.org/snippets/56/
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

dir = os.path.dirname( __file__ )
communication_directory = os.path.join( dir, 'communication' )
template_html_path = os.path.join( communication_directory, 'template/communication.html' )
template = open(template_html_path, 'r').read()

@app.route('/')
@crossdomain(origin='*')
def index():
    if app.debug:
        return open(template_html_path, 'r').read()
    return template


@socketio.on('event connect', namespace='/chat')
def event_connect(message):
    print(current_user.username + " connected")


@socketio.on('event broadcast', namespace='/chat')
def event_broadcast(message):
    print("broadcast")
    emit('event response',
            {'data': message['data'], 'user': current_user.username}, broadcast=True)

@socketio.on('event disconnect', namespace='/chat')
def event_disconnect(message):
    print("disconnected")
    disconnect()


@socketio.on('disconnect', namespace='/chat')
def event_disconnect():
    print("disconnected")


@socketio.on('join', namespace='/chat')
def join(message):
    print("join")
    join_room(message['room'])
    emit('event response room', {'data': message['room'], 'userjoin': message['userjoin']}, broadcast=True)


@socketio.on('leave', namespace='/chat')
def leave(message):
    leave_room(message['room'])
    emit('event response room',
         {'data': message['room'], 'userleave': message['userleave']}, broadcast=True)


@socketio.on('event room', namespace='/chat')
def send_room_message(message):
    emit('event response room',
         {'data': message['data'], 'chatroom': message['room']}, room=message['room'])

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Real-time communication server for Galaxy.')
    parser.add_argument('--port', type=int, default="7070", help='Port number on which the server should run.')
    parser.add_argument('--host', default='localhost', help='Hostname of the communication server.')

    args = parser.parse_args()
    socketio.run(app, host=args.host, port=args.port, debug=True)
