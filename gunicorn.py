# Gunicorn configuration settings.
import multiprocessing

bind = ":8211"
# Don't start too many workers:
workers = min(multiprocessing.cpu_count(), 4)
# Give workers an expiry:
max_requests = 2048
max_requests_jitter = 256
preload_app = True
