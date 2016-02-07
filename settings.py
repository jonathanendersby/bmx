# Who can call us?
# ALLOWED_HOSTS = ['123.132.123.123', '132.234.123.234']

# Alternatively set ALLOWED_HOSTS_ALL = True.
ALLOWED_HOSTS_ALL = True

API_KEYS = ["SUPERSECUREAPIKEY", ]

SCRIPTS = {'redeploy': {
    'description': 'git pull, collect_static, restart gunicorn, reload nginx etc.',
    'executable': '/var/www/someproject/scripts/somescript.sh',
    'email': ['dev1@foo.com', 'dev2@foo.com', ]
}}

MAILGUN_KEY = 'key-yoursuperawesomekeyhere'
MAILGUN_SANDBOX = 'sandbox0b08fexxxxxxxxxx9ae95fec5e.mailgun.org'
MAILGUN_FROM_ADDRESS = 'Some Name <foo@bar.com>'

try:
    from local_settings import *
except ImportError:
    pass


