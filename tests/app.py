import bottle

app = bottle.Bottle()

@app.route('/success')
def ok():
    return 'success'
