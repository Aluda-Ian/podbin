import os
import sys

# Add the backend directory to the sys.path
sys.path.insert(0, os.path.dirname(__file__))

from a2wsgi import ASGIMiddleware
from app.main import app

application = ASGIMiddleware(app)
