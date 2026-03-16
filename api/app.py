import sys
import os

sys.path.append(os.path.dirname(__file__) + "/..")

from app import app

# Vercel serverless entrypoint
def handler(request, response):
    return app(request.environ, response.start_response)