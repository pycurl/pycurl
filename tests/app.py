# -*- coding: utf-8 -*-
# vi:ts=4:et

import time as _time, sys
import flask
import werkzeug
try:
    import json
except ImportError:
    import simplejson as json

py3 = sys.version_info[0] == 3

app = flask.Flask(__name__)
app.debug = True

@app.route('/success')
def ok():
    return 'success'

@app.route('/short_wait')
def short_wait():
    _time.sleep(0.1)
    return 'success'

@app.route('/status/403')
def forbidden():
    return flask.Response('forbidden', 403)

@app.route('/status/404')
def not_found():
    return flask.Response('not found', 404)

@app.route('/postfields', methods=['GET', 'POST'])
def postfields():
    return json.dumps(dict(flask.request.form))

@app.route('/raw_utf8', methods=['POST'])
def raw_utf8():
    data = flask.request.data.decode('utf8')
    return json.dumps(data)

def xconvert_file(key, file):
    return {
        'key': key,
        'name': file.name,
        'filename': file.filename,
        'headers': file.headers,
        'content_type': file.content_type,
        'content_length': file.content_length,
        'data': file.read(),
    }

def convert_file(key, file):
    return {
        'name': file.name,
        'filename': file.filename,
        'data': file.read().decode(),
    }

@app.route('/files', methods=['POST'])
def files():
    files = [convert_file(key, flask.request.files[key]) for key in flask.request.files]
    return json.dumps(files)

@app.route('/header')
def header():
    return flask.request.headers.get(flask.request.args['h'], '')

# This is a hacky endpoint to test non-ascii text being given to libcurl
# via headers.
# HTTP RFC requires headers to be latin1-encoded.
# Any string can be decoded as latin1; here we encode the header value
# back into latin1 to obtain original bytestring, then decode it in utf-8.
# Thanks to bdarnell for the idea: https://github.com/pycurl/pycurl/issues/124
@app.route('/header_utf8')
def header_utf8():
    header_value = flask.request.headers.get(flask.request.args['h'], '' if py3 else b'')
    if py3:
        # header_value is a string, headers are decoded in latin1
        header_value = header_value.encode('latin1').decode('utf8')
    else:
        # header_value is a binary string, decode in utf-8 directly
        header_value = header_value.decode('utf8')
    return header_value

@app.route('/param_utf8_hack', methods=['POST'])
def param_utf8_hack():
    param = flask.request.form['p']
    return param

def pause_writer(interval):
    yield 'part1'
    _time.sleep(interval)
    yield 'part2'

@app.route('/pause')
def pause():
    return pause_writer(0.5)

@app.route('/long_pause')
def long_pause():
    return pause_writer(1)

@app.route('/utf8_body')
def utf8_body():
    # bottle encodes the body
    return 'Дружба народов'

@app.route('/invalid_utf8_body')
def invalid_utf8_body():
    return flask.Response(b'\xb3\xd2\xda\xcd\xd7', 200)

@app.route('/set_cookie_invalid_utf8')
def set_cookie_invalid_utf8():
    response = flask.Response('cookie set')
    # WARNING: The original bottle test passed '\xb3\xd2\xda\xcd\xd7...' as string
    # Presumably bottle encoded that as utf-8 in the response.
    # Flask on the other hand encodes such strings as latin-1 (chars in == bytes out).
    # In order to make the test pass I replicate the original bottle behavior by utf-8->latin1 roundtrip.
    response.headers['Set-Cookie'] = '\xb3\xd2\xda\xcd\xd7=%96%A6g%9Ay%B0%A5g%A7tm%7C%95%9A'.encode('utf-8').decode('latin-1')
    return response

@app.route('/content_type_invalid_utf8')
def content_type_invalid_utf8():
    response = flask.Response('content type set')
    # See the WARNING in set_cookie_invalid_utf8
    response.headers['Content-Type'] = '\xb3\xd2\xda\xcd\xd7'.encode('utf-8').decode('latin-1')
    return response

werkzeug.http.HTTP_STATUS_CODES[555] = '\xb3\xd2\xda\xcd\xd7'
@app.route('/status_invalid_utf8')
def status_invalid_utf8():
    return flask.Response(status=555)
