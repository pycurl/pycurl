import time as _time
import bottle
try:
    import json
except ImportError:
    import simplejson as json

app = bottle.Bottle()
app.debug = True

@app.route('/success')
def ok():
    return 'success'

@app.route('/short_wait')
def ok():
    _time.sleep(0.1)
    return 'success'

@app.route('/status/403')
def forbidden():
    return bottle.HTTPResponse('forbidden', 403)

@app.route('/status/404')
def not_found():
    return bottle.HTTPResponse('not found', 404)

@app.route('/postfields', method='post')
def postfields():
    return json.dumps(dict(bottle.request.forms))

@app.route('/raw_utf8', method='post')
def raw_utf8_repr():
    data = bottle.request.body.getvalue().decode('utf8')
    return json.dumps(data)

# XXX file is not a bottle FileUpload instance, but FieldStorage?
def convert_file(key, file):
    return {
        'key': key,
        'name': file.name,
        'raw_filename': file.raw_filename,
        'headers': file.headers,
        'content_type': file.content_type,
        'content_length': file.content_length,
        'data': file.read(),
    }

def convert_file(key, file):
    return {
        'name': file.name,
        'filename': file.filename,
        'data': file.file.read().decode(),
    }

@app.route('/files', method='post')
def files():
    files = [convert_file(key, bottle.request.files[key]) for key in bottle.request.files]
    return json.dumps(files)

@app.route('/header')
def header():
    return bottle.request.headers[bottle.request.query['h']]

# This is a hacky endpoint to test non-ascii text being given to libcurl
# via headers.
# HTTP RFC requires headers to be latin1-encoded.
# Any string can be decoded as latin1; here we encode the header value
# back into latin1 to obtain original bytestring, then decode it in utf-8.
# Thanks to bdarnell for the idea: https://github.com/pycurl/pycurl/issues/124
@app.route('/header_utf8')
def header():
    return bottle.request.headers[bottle.request.query['h']].encode('latin1').decode('utf8')

def pause_writer():
    yield 'part1'
    _time.sleep(0.5)
    yield 'part2'

@app.route('/pause')
def pause():
    return pause_writer()
