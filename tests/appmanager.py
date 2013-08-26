def setup(*specs):
    from . import runwsgi
    
    app_specs = []
    for spec in specs:
        app_module = __import__(spec[0], globals(), locals(), ['app'], 1)
        app = getattr(app_module, 'app')
        app_specs.append([app] + list(spec[1:]))
    
    return runwsgi.app_runner_setup(*app_specs)
