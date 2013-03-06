import bottle
try:
    import json
except ImportError:
    import simplejson as json

app = bottle.Bottle()

@app.route('/success')
def ok():
    return 'success'

@app.route('/status/403')
def forbidden():
    bottle.abort(403, 'forbidden')

@app.route('/status/404')
def not_found():
    bottle.abort(404, 'not found')

@app.route('/postfields', method='post')
def postfields():
    return json.dumps(dict(bottle.request.forms))

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
        'data': file.file.read(),
    }

@app.route('/files', method='post')
def files():
    files = [convert_file(key, bottle.request.files[key]) for key in bottle.request.files]
    return json.dumps(files)
