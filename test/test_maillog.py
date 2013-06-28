#!/usr/bin/python

import time
import unittest

from postfix_policy_rate_limit import MailLog


class MailLogTestCase(unittest.TestCase):

    def test_rate_limit_ok(self):
        mail_log = MailLog()
        for i in range(100):
            self.assertFalse(mail_log.user_violated_rate_limit(
                    "foo@example.com", time.time()))

    def test_rate_limit_violated(self):
        mail_log = MailLog()
        for i in range(199):
            mail_log.user_violated_rate_limit("foo@example.com", time.time())
        self.assertTrue(
            mail_log.user_violated_rate_limit("foo@example.com", time.time()))


if __name__ == "__main__":
    unittest.main()
