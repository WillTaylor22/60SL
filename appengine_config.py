from gaesessions import SessionMiddleware
import os

def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key="Asdnalskdnlkasndklasksjdflj3i;jer;oisfm9ocs9umflsjfl;js;lcjse;jm")
    return app