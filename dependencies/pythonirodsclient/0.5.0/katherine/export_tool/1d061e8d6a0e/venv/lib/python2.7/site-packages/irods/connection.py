import socket
import logging
import struct
import hashlib

from irods.message import (
    iRODSMessage, StartupPack, AuthResponse, AuthChallenge,
    OpenedDataObjRequest, FileSeekResponse, StringStringMap, VersionResponse)
from irods.exception import get_exception_by_code, NetworkException
from irods import MAX_PASSWORD_LENGTH
from irods.api_number import api_number

logger = logging.getLogger(__name__)


class Connection(object):

    def __init__(self, pool, account):
        self.pool = pool
        self.socket = None
        self.account = account
        self._server_version = self._connect()
        self._login()

    def __del__(self):
        if self.socket:
            self.disconnect()

    def send(self, message):
        str = message.pack()
        logger.debug(str)
        try:
            self.socket.sendall(str)
        except:
            logger.error(
                "Unable to send message. Connection to remote host may have closed. Releasing connection from pool.")
            self.release(True)
            raise NetworkException("Unable to send message")

    def recv(self):
        msg = iRODSMessage.recv(self.socket)
        if msg.int_info < 0:
            raise get_exception_by_code(msg.int_info)
        return msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def release(self, destroy=False):
        self.pool.release_connection(self, destroy)

    def reply(self, api_reply_index):
        value = socket.htonl(api_reply_index)
        try:
            self.socket.sendall(struct.pack('I', value))
        except:
            self.release(True)
            raise NetworkException("Unable to send API reply")

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((self.account.host, self.account.port))
        except socket.error:
            raise NetworkException("Could not connect to specified host and port: {host}:{port}".format(
                host=self.account.host, port=self.account.port))

        self.socket = s
        main_message = StartupPack(
            (self.account.proxy_user, self.account.proxy_zone),
            (self.account.client_user, self.account.client_zone)
        )

        msg = iRODSMessage(type='RODS_CONNECT', msg=main_message)
        self.send(msg)

        # server responds with version
        version_msg = self.recv()
        return version_msg.get_main_message(VersionResponse)

    @property
    def server_version(self):
        return self._server_version.relVersion

    def disconnect(self):
        disconnect_msg = iRODSMessage(type='RODS_DISCONNECT')
        self.send(disconnect_msg)
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None

    def _login(self):
        # authenticate
        auth_req = iRODSMessage(type='RODS_API_REQ', int_info=703)
        self.send(auth_req)

        # challenge
        challenge_msg = self.recv()
        logger.debug(challenge_msg.msg)
        challenge = challenge_msg.get_main_message(AuthChallenge).challenge
        padded_pwd = struct.pack(
            "%ds" % MAX_PASSWORD_LENGTH, self.account.password)
        m = hashlib.md5()
        m.update(challenge)
        m.update(padded_pwd)
        encoded_pwd = m.digest()

        encoded_pwd = encoded_pwd.replace('\x00', '\x01')
        pwd_msg = AuthResponse(
            response=encoded_pwd, username=self.account.proxy_user)
        pwd_request = iRODSMessage(
            type='RODS_API_REQ', int_info=704, msg=pwd_msg)
        self.send(pwd_request)

        auth_response = self.recv()

    def read_file(self, desc, size):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=size,
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_READ_AN'])

        logger.debug(desc)
        self.send(message)
        response = self.recv()
        return response.bs

    def write_file(self, desc, string):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=len(string),
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               bs=string,
                               int_info=api_number['DATA_OBJ_WRITE_AN'])
        self.send(message)
        response = self.recv()
        return response.int_info

    def seek_file(self, desc, offset, whence):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=0,
            whence=whence,
            oprType=0,
            offset=offset,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_LSEEK_AN'])

        self.send(message)
        response = self.recv()
        offset = response.get_main_message(FileSeekResponse).offset
        return offset

    def close_file(self, desc):
        message_body = OpenedDataObjRequest(
            l1descInx=desc,
            len=0,
            whence=0,
            oprType=0,
            offset=0,
            bytesWritten=0,
            KeyValPair_PI=StringStringMap()
        )
        message = iRODSMessage('RODS_API_REQ', msg=message_body,
                               int_info=api_number['DATA_OBJ_CLOSE_AN'])

        self.send(message)
        response = self.recv()
