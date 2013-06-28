#!/usr/bin/python

import socket
import subprocess
import threading
import unittest

import postfix_policy_rate_limit
from postfix_policy_rate_limit import (
    MailLog,
    PostfixPolicyServer,
)
#PostfixPolicyServer.allow_reuse_address = True

class PostfixPolicyServerTestCase(unittest.TestCase):

    def setUp(self):
        # globals suck
        postfix_policy_rate_limit.mail_log = MailLog()
        # the real stuff
        self.host = "localhost"
        self.port = 43243
        self.server = PostfixPolicyServer(self.host, self.port)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.client = socket.create_connection((self.host, self.port))

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()

    def _send_req_to_server(self):
        p = subprocess.Popen(["/bin/nc", self.host, str(self.port)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout, stderr) = p.communicate(
            "request=smtpd_access_policy\nsasl_username=foo\n\n")
        p.wait()
        return stdout

    def test_rate_limit_not_ok(self):
        for i in range(199):
            res = self._send_req_to_server()
            self.assertEqual(res, 'action=OK\n')
        res = self._send_req_to_server()
        self.assertEqual(res, 'action=550 violates rate limit\n')
        
    def test_rate_limit_ok(self):
        for i in range(10):
            res = self._send_req_to_server()
            self.assertEqual(res, 'action=OK\n')


if __name__ == "__main__":
    #import logging
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()
