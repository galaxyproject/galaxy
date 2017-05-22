"""
OpenID Connect Provider
"""
import logging

from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)

from future.backports.urllib.parse import parse_qs
import json
import os
import re
import sys
import traceback
import argparse
import importlib
from mako.lookup import TemplateLookup
from oic.oic.provider import AuthorizationEndpoint
from oic.oic.provider import EndSessionEndpoint
from oic.oic.provider import Provider
from oic.oic.provider import RegistrationEndpoint
from oic.oic.provider import TokenEndpoint
from oic.oic.provider import UserinfoEndpoint
from oic.utils import shelve_wrapper
from oic.utils.authn.authn_context import AuthnBroker
from oic.utils.authn.authn_context import make_auth_verify
from oic.utils.authn.client import verify_client
from oic.utils.authn.multi_auth import AuthnIndexedEndpointWrapper
from oic.utils.authn.user import UsernamePasswordMako
from oic.utils.authz import AuthzHandling
from oic.utils.http_util import *
from oic.utils.keyio import keyjar_init
from oic.utils.userinfo import UserInfo
from oic.utils.webfinger import OIC_ISSUER
from oic.utils.webfinger import WebFinger
from oic.utils.sdb import SessionDB


class OIDCConfig(object):
    # TODO: change the following two parameters as they are
    # TODO: initialized by the server knowing the port and address of the galaxy insntace.
    PORT = 8080
    ISSUER = 'http://127.0.0.1'  # do not include the port, it will be added in the code.

    SERVICEURL = "{issuer}verify"  # do not manually add issuer or port number, these will be added in the code.
    SERVER_CERT = "certification/server.crt"
    SERVER_KEY = "certification/server.key"
    CERT_CHAIN = None
    PASSWORD_ENDPOINT_INDEX = 0  # what is this, and what does its value mean?

    AUTHENTICATION = {
        "UserPassword":
            {
                "ACR": "PASSWORD",
                "WEIGHT": 1,
                "URL": SERVICEURL,
                "EndPoints": ["verify"],  # this endpoint is manually added to buildapp.py
            }
    }

    CLIENTDB = 'ClientDB'
    SYM_KEY = "SoLittleTime,Got"  # used for Symmetric key authentication only.
    COOKIENAME = 'pyoic'
    COOKIETTL = 4 * 60  # 4 hours

    USERINFO = "SIMPLE"

    USERDB = {
        "user1": {
            "sub": "sub1",
            "name": "name1",
            "given_name": "givenName1",
            "family_name": "familyName1",
            "nickname": "nickname1",
            "email": "email1@example.org",
            "email_verified": False,
            "phone_number": "+984400000000",
            "address": {
                "street_address": "address1",
                "locality": "locality1",
                "postal_code": "5719800000",
                "country": "Iran"
            },
        },
        "user2": {
            "sub": "sub2",
            "name": "name2",
            "given_name": "givenName2",
            "family_name": "familyName2",
            "nickname": "nickname2",
            "email": "email2@example.com",
            "email_verified": True,
            "address": {
                "street_address": "address2",
                "locality": "locality2",
                "region": "region2",
                "postal_code": "5719899999",
                "country": "Iran",
            },
        }
    }

    # This is a JSON Web Key (JWK) object, and its members represent
    # properties of the key and its values.
    keys = [
        {"type": "RSA", "key": "cryptography_keys/key.pem", "use": ["enc", "sig"]},
        {"type": "EC", "crv": "P-256", "use": ["sig"]},
        {"type": "EC", "crv": "P-256", "use": ["enc"]}

        # "type" or "kty" identifies the cryptographic algorithm family used with the key.
        # The kty values are case sensitive. The kty values should either be registered
        # in the IANA "JSON Web Key Types" registery or be a value that contains a
        # Collision-Resistant Name. For more info on kty values refer to:
        # https://tools.ietf.org/html/rfc7518
        #
        # Cryptography keys are: private and public keys.
        # Keys are encrypted with RSA algorithm, and are stored in separate files in RSA.
        #
        # use (Public Key Use) parameter identifies the intended use of the public key.
        # This parameter is employed to indicate whether a public key is used for encryption
        # data or verifying the signature on data. Values defined by this specification are:
        # enc (encryption), sig (signature)
        #
        #
        # "RSA" (a public key cryptography), see:
        # http://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf
        #
        # "EC": Elliptic Curve, see:
        # http://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf
    ]


class OIDCProvider(BaseUIController):
    """
    This class implements an OpenID Connect Provider,
    which enables Galaxy users to login to OpenID 
    Connect Relying Parties (e.g., Amazon AWS) using 
    their Galaxy credentials. 
    """

    def __init__(self, app):
        self.urls = []
        # self.provider = self.setup_oidc_provider(app.config.oidc_idp_config_file)
        self.provider = self.setup_oidc_provider(OIDCConfig)
        self.endpoints = [
            AuthorizationEndpoint(self.authorization),
            TokenEndpoint(self.token),
            UserinfoEndpoint(self.userinfo),
            RegistrationEndpoint(self.registration),
            EndSessionEndpoint(self.endsession),
        ]
        self.provider.endpoints = self.endpoints
        for endp in self.endpoints:
            self.urls.append(("^%s" % endp.etype, endp.func))

    def setup_oidc_provider(self, oidcConfig):
        # TODO: root should read it's value from Galaxy, not a hard-coded path like this. Update it.
        root = '/Users/vahid/pyProjects/galaxy/lib/galaxy/webapps/galaxy/controllers/'
        lookup = TemplateLookup(directories=[root + 'Templates', root + 'htdocs'],
                                module_directory=root + 'modules',
                                input_encoding='utf-8', output_encoding='utf-8')

        usernamePasswords = {
            "user1": "1",
            "user2": "2"
        }

        # JWKS: JSON Web Key
        jwksFileName = "static/jwks.json"
        if oidcConfig.PORT:
            oidcConfig.ISSUER = oidcConfig.ISSUER + ':{}/{}/'.format(oidcConfig.PORT, "oidc")
        else:
            oidcConfig.ISSUER = oidcConfig.ISSUER + '/{}/'.format("oidc")
        oidcConfig.SERVICEURL = oidcConfig.SERVICEURL.format(issuer=oidcConfig.ISSUER)
        endPoints = oidcConfig.AUTHENTICATION["UserPassword"]["EndPoints"]
        fullEndPointsPath = ["%s%s" % (oidcConfig.ISSUER, ep) for ep in endPoints]

        # TODO: why this instantiation happens so early? can I move it later?
        # An OIDC Authorization/Authentication server is designed to
        # allow more than one authentication method to be used by the server.
        # And that is what the AuthBroker is for.
        # Given information about the authorisation request, the AuthBroker
        # chooses which method(s) to be used for authenticating the person/entity.
        # According to the OIDC standard a Relaying Party can say
        # 'I want this type of authentication', and the AuthnBroker tries to pick
        # methods from the set it has been supplied, to map that request.
        authnBroker = AuthnBroker()

        # UsernamePasswordMako: authenticas a user using the username/password form in a
        # WSGI environment using Mako as template system
        usernamePasswordAuthn = UsernamePasswordMako(
            None,  # server instance
            "login.mako",  # a mako template
            lookup,  # lookup template
            usernamePasswords,  # username/password dictionary-like database
            "%sauthorization" % oidcConfig.ISSUER,  # where to send the user after authentication
            None,  # templ_arg_func ??!!
            fullEndPointsPath)  # verification endpoints

        # AuthnIndexedEndpointWrapper is a wrapper class for using an authentication module with multiple endpoints.
        self.authnIndexedEndPointWrapper = AuthnIndexedEndpointWrapper(usernamePasswordAuthn,
                                                                       oidcConfig.PASSWORD_ENDPOINT_INDEX)

        authnBroker.add(oidcConfig.AUTHENTICATION["UserPassword"]["ACR"],  # (?!)
                        self.authnIndexedEndPointWrapper,  # (?!) method: an identifier of the authentication method.
                        oidcConfig.AUTHENTICATION["UserPassword"]["WEIGHT"],  # security level
                        "")  # (?!) authentication authority

        authz = AuthzHandling()
        # clientDB = shelve_wrapper.open("ClientDB")
        clientDB = shelve_wrapper.open(oidcConfig.CLIENTDB)

        provider = Provider(
            name=oidcConfig.ISSUER,  # name
            sdb=SessionDB(oidcConfig.ISSUER),  # session database.
            cdb=clientDB,  # client database
            authn_broker=authnBroker,  # authn broker
            userinfo=None,  # user information
            authz=authz,  # authz
            client_authn=verify_client,  # client authentication
            symkey=oidcConfig.SYM_KEY,  # Used for Symmetric key authentication
            # urlmap = None,                               # ?
            # ca_certs = "",                               # ?
            # keyjar = None,                               # ?
            # hostname = "",                               # ?
            template_lookup=lookup,  # ?
            template={"form_post": "form_response.mako"},  # ?
            # verify_ssl = True,                           # ?
            # capabilities = None,                         # ?
            # schema = OpenIDSchema,                       # ?
            # jwks_uri = '',                               # ?
            # jwks_name = '',                              # ?
            baseurl=oidcConfig.ISSUER,
            # client_cert = None                           # ?
        )

        # SessionDB:
        # This is database where the provider keeps information about
        # the authenticated/authorised users. It includes information
        # such as "what has been asked for (claims, scopes, and etc. )"
        # and "the state of the session". There is one entry in the
        # database per person
        #
        # __________ Note __________
        # provider.keyjar is an interesting parameter,
        # currently it uses default values, but
        # if you have time, it worth investigating.

        for authnIndexedEndPointWrapper in authnBroker:
            authnIndexedEndPointWrapper.srv = provider

        # TODO: this is a point to consider: what if user data are in a database?
        if oidcConfig.USERINFO == "SIMPLE":
            provider.userinfo = UserInfo(oidcConfig.USERDB)

        provider.cookie_ttl = oidcConfig.COOKIETTL
        provider.cookie_name = oidcConfig.COOKIENAME

        provider.debug = True

        try:
            # JWK: JSON Web Key
            # JWKS: is a dictionary of JWK
            # __________ NOTE __________
            # JWKS contains private key information.
            #
            # keyjar_init configures cryptographic key
            # based on the provided configuration "keys".
            jwks = keyjar_init(
                provider,  # server/client instance
                oidcConfig.keys,  # key configuration
                oidcConfig.keys,  # key configuration
                kid_template="op%d")  # template by which to build the kids (key ID parameter)
        except Exception as err:
            provider.key_setup("static", sig={"format": "jwk", "alg": "rsa"})
        else:
            for key in jwks["keys"]:
                for k in key.keys():
                    key[k] = as_unicode(key[k])

            f = open(jwksFileName, "w")
            f.write(json.dumps(jwks))
            f.close()
            provider.jwks_uri = "%s%s" % (provider.baseurl, jwksFileName)

        endPoint = OIDCConfig.AUTHENTICATION["UserPassword"]["EndPoints"][OIDCConfig.PASSWORD_ENDPOINT_INDEX]
        self.urls.append((r'^' + endPoint, make_auth_verify(self.authnIndexedEndPointWrapper.verify)))
        self.urls.extend([
            (r'^oidc/.well-known/openid-configuration', self.op_info),
            (r'^oidc/.well-known/simple-web-discovery', self.swd_info),
            (r'^oidc/.well-known/host-meta.json', self.meta_info),
            (r'^oidc/.well-known/webfinger', self.webfinger),
            (r'oidc/.+\.css$', self.css),
            (r'oidc/safe', self.safe),
            (r'^oidc/keyrollover', self.key_rollover),
            (r'^oidc/clearkeys', self.clear_keys),
            (r'^oidc/check_session', self.check_session_iframe)
            #    (r'tracelog', trace_log),
        ])

        return provider

    @web.expose
    def verify(self, trans, **kwargs):
        return self.provider.verify_endpoint(request=kwargs)

    @web.expose
    # noinspection PyUnusedLocal
    def authorization(self, trans, **kwargs):
        return self.provider.authorization_endpoint(kwargs)

    @web.expose
    # noinspection PyUnusedLocal
    def op_info(self, trans):
        print '\n\n\n\n in op info \n\n\n\n\n\n\n'
        return self.provider.providerinfo_endpoint()

    @web.expose
    # noinspection PyUnusedLocal
    def registration(self, trans):
        if trans.environ["REQUEST_METHOD"] == "POST":
            return self.provider.registration_endpoint(trans.request.body)
        elif trans["REQUEST_METHOD"] == "GET":
            return self.provider.read_registration()
        else:
            resp = ServiceError("Method not supported")
            # TODO: fix the following call.
            return resp(trans, start_response)

    # noinspection PyUnusedLocal
    def check_id(self, environ, start_response):
        return self.provider.check_id_endpoint()

    @web.expose
    # noinspection PyUnusedLocal
    def swd_info(self, environ):
        return self.provider.discovery_endpoint()

    # noinspection PyUnusedLocal
    def trace_log(self, environ, start_response):
        return self.provider.tracelog_endpoint()

    @web.expose
    # noinspection PyUnusedLocal
    def meta_info(self, environ):
        """
        Returns something like this::

             {"links":[
                 {
                    "rel":"http://openid.net/specs/connect/1.0/issuer",
                    "href":"https://openidconnect.info/"
                 }
             ]}

        """
        pass

    @web.expose
    def webfinger(self, environ):
        # TODO: This endpoint is not tested.
        query = parse_qs(environ["QUERY_STRING"])
        try:
            assert query["rel"] == [OIC_ISSUER]
            resource = query["resource"][0]
        except KeyError:
            resp = BadRequest("Missing parameter in request")
        else:
            wf = WebFinger()
            resp = Response(wf.response(subject=resource,
                                        base=self.provider.baseurl))
        return resp(environ, start_response)

    @web.expose
    # noinspection PyUnusedLocal
    def css(self, environ):
        # TODO: double check this endpoint
        try:
            info = open(environ["PATH_INFO"]).read()
            resp = Response(info)
        except (OSError, IOError):
            resp = NotFound(environ["PATH_INFO"])

        # TODO: this is wrong ! what's the correct method of calling resp?
        return resp(environ, start_response)

    # noinspection PyUnusedLocal
    def endsession(self, environ, start_response):
        return self.provider.endsession_endpoint

    # noinspection PyUnusedLocal
    def token(self, trans, **kwargs):
        # TODO: double check this endpoint
        return self.provider.token_endpoint()

    @web.expose
    def safe(self, environ):
        # TODO: double check this endpoint -- it's not tested.
        _srv = self.provider.server
        # _log_info = self.provider.logger.info
        # _log_info("- safe -")
        # _log_info("env: %s" % environ)
        # _log_info("handle: %s" % (handle,))

        try:
            authz = environ["HTTP_AUTHORIZATION"]
            (typ, code) = authz.split(" ")
            assert typ == "Bearer"
        except KeyError:
            resp = BadRequest("Missing authorization information")
            # TODO: this is wrong ! what's the correct method of calling resp?
            return resp(environ, start_response)

        try:
            _sinfo = _srv.sdb[code]
        except KeyError:
            resp = Unauthorized("Not authorized")
            # TODO: this is wrong ! what's the correct method of calling resp?
            return resp(environ, start_response)

        info = "'%s' secrets" % _sinfo["sub"]
        # TODO: this is wrong ! what's the correct method of calling resp?
        resp = Response(info)
        return resp(environ, start_response)

    @web.expose
    def check_session_iframe(self, environ):
        # TODO: This endpoint is not checked!
        return static(self, environ, start_response, "htdocs/op_session_iframe.html")

    @web.expose
    def clear_keys(self, environ):
        # TODO: this endpoint is not checked!
        provider.remove_inactive_keys()
        resp = Response("OK")
        # TODO: this is wrong ! what's the correct method of calling resp?
        return resp(environ, start_response)

    @web.expose
    def key_rollover(self, environ):
        # TODO: This is endpoint is to be tested!
        # expects a post containing the necessary information
        _txt = get_post(environ)
        _jwks = json.loads(_txt)
        # logger.info("Key rollover to")
        provider.do_key_rollover(_jwks, "key_%d_%%d" % int(time.time()))
        # Dump to file
        f = open(jwksFileName, "w")
        f.write(json.dumps(provider.keyjar.export_jwks()))
        f.close()
        resp = Response("OK")
        return resp(environ, start_response)

    # noinspection PyUnusedLocal
    def userinfo(self, trans):
        # TODO: double check this endpoint
        return self.provider.userinfo_endpoint

    # TODO: this function is not used - To be deleted!
    def oidc(self, trans, **kwd):
        """
        Handles user request to access an OpenID provider
        :param environ: The HTTP application environment
        :param start_response: The application to run when the handling of the request is done
        :return: The response as a list of lines
        """
        # path = trans.get('PATH_INFO', '').lstrip('/')
        # print 'trans.app: \n', trans.app
        # print '\n trans.app.config: \n', trans.app.config
        # print '\n oidc_idp_config_file: \n', trans.app.config.oidc_idp_config_file
        # print '\n trans.app.__call__: \n', trans.app.__name__
        # print '\n trans.environ: \n', trans.environ
        # print '\n handle request: \n', trans.start_response
        # print '\n trans.start_response: \n', start_response

        # path = kwd['sub1'] + '/' + kwd['sub2']
        path = trans.environ.get('PATH_INFO', '').lstrip('/')
        if path == "robots.txt":
            return static(self, trans.environ, start_response, "static/robots.txt")

        trans.environ["oic.oas"] = self.provider
        if path.startswith("static/"):
            return static(self, trans.environ, start_response, path)
        for regex, callback in self.urls:
            match = re.search(regex, path)
            if match is not None:
                try:
                    trans.environ['oic.url_args'] = match.groups()[0]
                except IndexError:
                    trans.environ['oic.url_args'] = path
                try:
                    return callback(trans)
                except Exception as err:
                    message = traceback.format_exception(*sys.exc_info())
                    logger.exception("%s" % err)
                    resp = ServiceError("%s" % err)
                    return resp(trans.environ, start_response)
        resp = NotFound("Couldn't find the side you asked for!")
        return resp(trans.environ, start_response)
