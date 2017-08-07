"""
OAuth 2.0 and OpenID Connect Authentication and Authorization Controller.
"""

from __future__ import absolute_import
import logging
log = logging.getLogger(__name__)
from galaxy import web
from galaxy.web.base.controller import BaseUIController
from oauth2client import client
import requests
import hashlib

class OAuth2( BaseUIController ):

    @web.expose
    def authenticate(self, trans, **kwargs):
        return

    @web.expose
    def callback(self, trans, **kwargs):
        return
