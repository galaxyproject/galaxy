#!/usr/bin/env python

"""
Server for realtime communication between Galaxy uers.

At first you need to install a few requirements.

. GALAXY_ROOT/.venv/bin/activate                        # activate Galaxy's virtualenv
pip install flask flask-login flask-socketio eventlet   # install the requirements

As a next step start the communication server with something like this:

./scripts/communication/communication_server.py --port 7070 --host localhost

Please make sure the host and the port matches the ones in ./config/galaxy.ini and
to set the `secret_id`.

This communication server can be controlled on three different levels:
  1. The admin can activate/deactivate the communication server via ./config/galaxy.ini. [off by default]
  2. The user can activate/deactivate it in their own personal-settings via Galaxy user preferences. [off by default]
  3. The user can activate/deactivate communications for a session directly in the communication window. [on by default]
"""

import argparse
import hashlib
import logging
import os
import sys
from datetime import timedelta
from functools import update_wrapper

import flask.ext.login as flask_login
import six
from flask import (
    current_app,
    Flask,
    make_response,
    request,
    send_file
)
from flask.ext.login import current_user
from flask_socketio import (
    disconnect,
    emit,
    join_room,
    leave_room,
    SocketIO
)

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.config
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.script import app_properties_from_args, populate_config_args
from galaxy.web.security import SecurityHelper

logging.basicConfig()
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Real-time communication server for Galaxy.')
parser.add_argument('--port', type=int, default="7070", help='Port number on which the server should run.')
parser.add_argument('--host', default='localhost', help='Hostname of the communication server.')
populate_config_args(parser)
args = parser.parse_args()

# With the config file we can load the full app properties
app_properties = app_properties_from_args(args)

config = galaxy.config.Configuration(**app_properties)
model = galaxy.config.init_models_from_config(config)
sa_session = model.context.current

# We need the ID secret for configuring the security helper to decrypt
# galaxysession cookies.
if "id_secret" not in app_properties:
    log.warning('No ID_SECRET specified. Please set the "id_secret" in your galaxy.ini.')

id_secret = app_properties.get('id_secret', 'dangerous_default')

security_helper = SecurityHelper(id_secret=id_secret)
# And get access to the models
# Login manager to manage current_user functionality
login_manager = flask_login.LoginManager()

app = Flask(__name__)
app.config['SECRET_KEY'] = id_secret
login_manager.init_app(app)
socketio = SocketIO(app)


@login_manager.request_loader
def findUserByCookie(request):
    cookie_value = request.cookies.get('galaxysession')
    if not cookie_value:
        return None

    session_key = security_helper.decode_guid(cookie_value)
    user_session = sa_session.query(model.GalaxySession).filter_by(session_key=session_key).first()

    if user_session:
        return user_session.user

    return None


# Taken from flask.pocoo.org/snippets/56/
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, six.string_types):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, six.string_types):
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


script_dir = os.path.dirname(os.path.realpath(__file__))
communication_directory = os.path.join(script_dir, 'template')


@app.route('/')
@crossdomain(origin='*')
def index():
    return send_file(os.path.join(communication_directory, 'communication.html'))


@app.route('/communication.js')
def static_script():
    return send_file(os.path.join(communication_directory, 'communication.js'))


@app.route('/communication.css')
def static_style():
    return send_file(os.path.join(communication_directory, 'communication.css'))


@socketio.on('event connect', namespace='/chat')
def event_connect(message):
    log.info("%s connected" % (current_user.username,))


@socketio.on('event broadcast', namespace='/chat')
def event_broadcast(message):
    message = sanitize_html(message['data'])

    log.debug("%s broadcast '%s'" % (current_user.username, message))

    emit('event response',
        {'data': message, 'user': current_user.username, 'gravatar': hashlib.md5(current_user.email).hexdigest()}, broadcast=True)


@socketio.on('event room', namespace='/chat')
def send_room_message(message):
    data = sanitize_html(message['data'])
    room = sanitize_html(message['room'])

    log.debug("%s sent '%s' to %s" % (current_user.username, message, room))

    emit('event response room',
        {'data': data, 'user': current_user.username, 'gravatar': hashlib.md5(current_user.email).hexdigest(), 'chatroom': room}, room=room)


@socketio.on('event disconnect', namespace='/chat')
def event_disconnect(message):
    log.info("%s disconnected" % current_user.username)
    disconnect()


@socketio.on('join', namespace='/chat')
def join(message):
    room = sanitize_html(message['room'])

    log.debug("%s joined %s" % (current_user.username, room))
    join_room(room)

    emit('event response room',
        {'data': room, 'userjoin': current_user.username}, broadcast=True)


@socketio.on('leave', namespace='/chat')
def leave(message):
    room = sanitize_html(message['room'])

    log.debug("%s left %s" % (current_user.username, room))
    leave_room(room)

    emit('event response room',
        {'data': room, 'userleave': current_user.username}, broadcast=True)


if __name__ == '__main__':
    socketio.run(app, host=args.host, port=args.port)
