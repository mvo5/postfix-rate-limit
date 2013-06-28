#!/usr/bin/python

import logging
import time

from threading import Semaphore

import SocketServer
from StringIO import StringIO


class MailLog(object):
    MAX_MAILS = 200     # maimum mails
    MAX_TIME = 60*60    # per time (e.g. 200/1h)

    def __init__(self):
        self._mail_log = {}
        self._mail_log_lock = Semaphore()

    def _log_mail(self, from_user, mail_time):
        # append the new mail
        l = self._mail_log.get(from_user, [])
        l.append(mail_time)
        # keep at a limited size
        if len(l) > self.MAX_MAILS:
            l.pop(0)
        self._mail_log[from_user] = l

    def _get_mail_count_for_user(self, username):
        return len(self._mail_log.get(username, []))
    
    def _get_time_delta_of_first_mail(self, username):
        l = self._mail_log.get(username, [])
        if not l:
            return None
        first_time = l[0]
        delta = time.time() - first_time
        return delta

    def user_violated_rate_limit(self, from_user, mail_time):
        # we are multi threaded
        self._mail_log_lock.acquire()
        # build data
        self._log_mail(from_user, mail_time)
        mail_count = self._get_mail_count_for_user(from_user)
        time_delta =  self._get_time_delta_of_first_mail(from_user)
        # release lock
        self._mail_log_lock.release()
        if (mail_count == self.MAX_MAILS and 
            time_delta < self.MAX_TIME):
            logging.warn("user: '%s' violated the rate limit" % from_user)
            return True
        return False


class RequestHandler(SocketServer.BaseRequestHandler):

    def _read_blocking(self):
        # self.request is the TCP socket connected to the client
        data = ""
        while True:
            chunk = self.request.recv(1024)
            if not chunk:
                break
            data += chunk
        return data

    def parse_data_block(self, stream):
        block = {}
        while True:
            line = stream.readline().strip()
            if line == "":
                break
            k,sep,v = line.partition("=")
            block[k] = v
        return block

    def handle(self):
        # read/parse
        data = self._read_blocking()
        req = self.parse_data_block(StringIO(data))
        logging.debug("got req: %s" % req)
        # do something
        request_type = req.get("request", "") 
        if request_type != "smtpd_access_policy":
            logging.warn("unknown request type '%s'" % request_type)
            return False
        username = req.get("sasl_username", None)
        if not username:
            logging.info(
                "missing 'sasl_username' in request block got '%s'" %  username)
            return False
        # check request
        action="OK"
        now = time.time()
        if mail_log.user_violated_rate_limit(username, now):
            action="550 violates rate limit"
        self.request.sendall("action=%s\n" % action)

        
# FIXME: *ick* global!
mail_log = MailLog()

class PostfixPolicyServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    def __init__(self, host, port):
        SocketServer.TCPServer.__init__(self, (host, port), RequestHandler)


if __name__ == "__main__":
    HOST = "localhost"
    PORT = 5834

    server = PostfixPolicyServer(HOST, PORT)
    server.serve_forever()

