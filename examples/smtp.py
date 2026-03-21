# Based on the simple libcurl SMTP example:
# https://github.com/bagder/curl/blob/master/docs/examples/smtp-mail.c
# There are other SMTP examples in that directory that you may find helpful.

from . import localhost
import pycurl
from io import BytesIO

mail_server = 'smtp://%s' % localhost
mail_from = 'sender@example.org'
mail_to = 'addressee@example.net'

c = pycurl.Curl()
c.setopt(c.URL, mail_server)
c.setopt(c.MAIL_FROM, mail_from)
c.setopt(c.MAIL_RCPT, [mail_to])

message = '''\
From: %s
To: %s
Subject: PycURL SMTP example

SMTP example via PycURL
''' % (mail_from, mail_to)

message = message.encode('ascii')

# libcurl does not perform buffering, therefore
# we need to wrap the message string into a BytesIO.
io = BytesIO(message)
c.setopt(c.READDATA, io)

# If UPLOAD is not set, libcurl performs SMTP VRFY.
c.setopt(c.UPLOAD, 1)

c.perform()
c.close()
