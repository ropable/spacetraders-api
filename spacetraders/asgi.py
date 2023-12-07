"""
ASGI config for spacetraders project.
It exposes the ASGI callable as a module-level variable named ``application``.
"""
from django.core.asgi import get_asgi_application
import os
from pathlib import Path

d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spacetraders.settings")
application = get_asgi_application()
