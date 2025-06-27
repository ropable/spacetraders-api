"""
WSGI config for spacetraders project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv

    load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spacetraders.settings")
application = get_wsgi_application()
