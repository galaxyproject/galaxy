#!/usr/bin/env python
"""
check_galaxy can be run by hand, although it is meant to run from cron
via the check_galaxy.sh script in Galaxy's cron/ directory.
"""
from __future__ import print_function

import formatter
import getopt
import htmllib
import json
import os
import socket
import sys
import time
import warnings
from user import home

from six.moves.urllib.request import (
    build_opener,
    HTTPCookieProcessor,
    Request
)

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import twill.commands as tc

# options
if "DEBUG" in os.environ:
    debug = os.environ["DEBUG"]
else:
    debug = False


# handle arg(s)
def usage():
    sys.exit("usage: check_galaxy.py <server> <username> <password> <handler>")


try:
    opts, args = getopt.getopt(sys.argv[1:], 'n')
except getopt.GetoptError as e:
    print(str(e))
    usage()
if len(args) < 1:
    usage()
server = args[0]
username = args[1]
password = args[2]
handler = args[3]
warntime = 240

new_history = False
for o, a in opts:
    if o == "-n":
        if debug:
            print("Specified -n, will create a new history")
        new_history = True
    else:
        usage()

# state information
var_dir = os.path.join(home, ".check_galaxy", server.replace('http://', '').replace('https://', ''), handler)
if not os.access(var_dir, os.F_OK):
    os.makedirs(var_dir, 0o700)

# default timeout for twill browser is never
socket.setdefaulttimeout(60)

# user-agent
tc.agent("Mozilla/5.0 (compatible; check_galaxy/0.2)")
tc.config('use_tidy', 0)


class Browser(object):
    def __init__(self):
        self.server = server
        self.handler = handler
        self.waited = -1
        self.tool = 'echo_' + handler
        self._hda_id = None
        self._hda_state = None
        self._history_id = None
        if not self.server.startswith('http'):
            self.server = 'http://' + self.server
        self.cookie_jar = os.path.join(var_dir, "cookie_jar")
        dprint("cookie jar path: %s" % self.cookie_jar)
        if not os.access(self.cookie_jar, os.R_OK):
            dprint("no cookie jar at above path, creating")
            tc.save_cookies(self.cookie_jar)
        tc.load_cookies(self.cookie_jar)
        self.opener = build_opener(HTTPCookieProcessor(tc.get_browser().cj))

    def get(self, path):
        tc.go("%s%s" % (self.server, path))
        tc.code(200)

    def req(self, path, data=None, method=None):
        url = self.server + path
        if data:
            req = Request(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data))
        else:
            req = Request(url, headers={'Content-Type': 'application/json'})
        if method:
            req.get_method = lambda: method
        res = self.opener.open(req)
        print('==> at %s (%s)' % (url, method or 'GET'))
        assert res.getcode() == 200, url
        return res

    def reset(self):
        self._hda_id = None
        self._hda_state = None
        self._history_id = None
        if new_history:
            self.delete_history()
            self.create_history()
        self.delete_datasets()

    def delete_history(self):
        # note, this could cause a history to be created and then deleted.  i don't care.
        self.req('/api/histories/%s' % self.history_id, method='DELETE')

    def login(self, user, pw):
        self.get("/user/login")
        tc.fv("1", "login", user)
        tc.fv("1", "password", pw)
        tc.submit("Login")
        tc.code(200)
        if len(tc.get_browser().get_all_forms()) > 0:
            # uh ohs, fail
            p = userParser()
            p.feed(tc.browser.get_html())
            if p.bad_pw:
                raise Exception("Password is incorrect")
            else:
                raise Exception("Unknown error logging in")
        tc.save_cookies(self.cookie_jar)

    def runtool(self):
        path = '/api/tools'
        data = {'tool_id' : self.tool,
                'history_id' : self.history_id,
                'inputs' : {'echo' : self.handler}}
        res = self.req(path, data=data)
        dprint(json.loads(res.read()))

    @property
    def history_id(self):
        if self._history_id is None:
            self.get('/api/histories')
            for history in json.loads(tc.browser.get_html()):
                # find an undeleted history named the same as the handler
                if history['name'] == self.handler:
                    self._history_id = history['id']
                    break
            else:
                self.create_history()
        return self._history_id

    def create_history(self):
        res = self.req('/api/histories', data={'name' : handler})
        self._history_id = json.loads(res.read())['id']

    @property
    def history_contents(self):
        self.get('/api/histories/%s/contents' % self.history_id)
        return json.loads(tc.browser.get_html())

    @property
    def hda_id(self):
        if self._hda_id is None:
            self.set_top_hda()
        return self._hda_id

    @property
    def hda_state(self):
        if self._hda_state is None:
            self.set_top_hda()
        return self._hda_state

    def set_top_hda(self):
        self.get(self.history_contents[-1]['url'])
        hda = json.loads(tc.browser.get_html())
        self._hda_id = hda['id']
        self._hda_state = hda['state']

    @property
    def undeleted_hdas(self):
        rval = []
        for item in self.history_contents:
            self.get(item['url'])
            hda = json.loads(tc.browser.get_html())
            if hda['deleted'] is False:
                rval.append(hda)
        return rval

    @property
    def history_state(self):
        self.get('/api/histories/%s' % self.history_id)
        return json.loads(tc.browser.get_html())['state']

    @property
    def history_state_terminal(self):
        if self.history_state not in ['queued', 'running', 'paused']:
            return True
        return False

    def wait(self):
        sleep_amount = 1
        count = 0
        maxiter = 20
        start = time.time()
        while count < maxiter:
            count += 1
            if not self.history_state_terminal:
                time.sleep(sleep_amount)
                sleep_amount += 1
            else:
                break
        self.waited = time.time() - start
        assert count < maxiter, "Job timeout, waited %.2f seconds" % self.waited

    def check_state(self):
        if self.hda_state != "ok":
            self.get("/datasets/%s/stderr" % self.hda_id)
            print(tc.browser.get_html())
            raise Exception("HDA %s NOT OK: %s" % (self.hda_id, self.hda_state))

    def check_hda_content(self):
        self.get("/datasets/%s/display?to_ext=txt" % self.hda_id)
        data = tc.browser.get_html().strip()
        if data == self.handler:
            dprint("Tool output is correct: %s" % data)
        else:
            dprint("EXPECTED: %s" % self.handler)
            dprint("GOT: %s" % data)
            raise Exception("Tool output differs from expected")

    def delete_datasets(self):
        for hda in self.undeleted_hdas:
            path = '/api/histories/%s/contents/%s' % (self.history_id, hda['id'])
            self.req(path, method='DELETE')
        hdas = [hda['id'] for hda in self.undeleted_hdas]
        if hdas:
            print("Remaining datasets ids:", " ".join(hdas))
            raise Exception("History still contains datasets after attempting to delete them")

    def check_if_logged_in(self, user):
        try:
            return json.loads(self.req('/api/users').read())[0]['email'] == user
        except Exception as e:
            print('Exception checking if logged in: %s' % str(e))
            return False


class userParser(htmllib.HTMLParser):
    def __init__(self):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.in_span = False
        self.in_div = False
        self.no_user = False
        self.bad_pw = False
        self.already_exists = False

    def start_span(self, attrs):
        self.in_span = True

    def start_div(self, attrs):
        self.in_div = True

    def end_span(self):
        self.in_span = False

    def end_div(self):
        self.in_div = False

    def handle_data(self, data):
        if self.in_span or self.in_div:
            if data == "No such user (please note that login is case sensitive)":
                self.no_user = True
            elif data == "Invalid password":
                self.bad_pw = True
            elif data == "User with that email already exists":
                self.already_exists = True


def dprint(str):
    if debug:
        print(str)


if __name__ == "__main__":

    dprint("checking %s" % server)

    b = Browser()

    # login (or not)
    if b.check_if_logged_in(username):
        dprint("we are already logged in (via cookies), hooray!")
    else:
        dprint("not logged in... logging in")
        b.login(username, password)

    # make sure history and state is clean
    b.reset()

    b.runtool()
    b.wait()
    b.check_state()
    b.check_hda_content()
    b.delete_datasets()

    assert b.waited <= warntime, "Warning: Job runtime: %.2f" % b.waited

    print("OK: Job runtime: %.2f" % b.waited)
    sys.exit(0)
