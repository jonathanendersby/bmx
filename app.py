from flask import Flask
from flask import request
import requests
import subprocess

import settings


app = Flask(__name__)


class AllowedHostsOverlapException(Exception):
    pass


class DefaultAPIKeyStillConfiguredException(Exception):
    pass


class UnallowedHostException(Exception):
    pass


class APIKeyException(Exception):
    pass


class UnknownScriptException(Exception):
    pass


def check_setting_sanity():
    # Quick gotcha check to make sure you haven't got a confused config that might bite yo ass.
    if hasattr(settings, 'ALLOWED_HOSTS') and hasattr(settings, 'ALLOWED_HOSTS_ALL'):
        if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS_ALL:
            raise AllowedHostsOverlapException('You can not have both ALLOWED_HOSTS configured and '
                                               'ALLOWED_HOSTS_ALL set to True.')

    # Check that we don't have the example API key still configured.
    if "SUPERSECUREAPIKEY" in settings.API_KEYS:
        raise DefaultAPIKeyStillConfiguredException('Please remove "SUPERSECUREAPIKEY" from your settings file.')


def build_html_output(script, output, returncode, os_errors, subprocess_errors):
    out = ""
    print script

    out += "<h2>Script: %s</h2>" % script['executable']
    out += "<h2>Return Code: %s</h2>" % returncode
    out += "<h2>Output</h2>%s" % output
    out += "<h2>OS Errors</h2>%s" % os_errors
    out += "<h2>Subprocess Errors</h2>%s" % subprocess_errors

    return out


def send_mail(script, output, returncode, os_errors, subprocess_errors):

    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(settings.MAILGUN_SANDBOX)
    html = build_html_output(script, output, returncode, os_errors, subprocess_errors)

    for email in script['email']:
        mg = requests.post(request_url, auth=('api', settings.MAILGUN_KEY), data={
            'from': 'devops@io.co.za',
            'to': email,
            'subject': 'BMX: ',
            'html': html
        })

        print 'Sending to %s' % email
        print 'Status: {0}'.format(mg.status_code)
        print 'Body:   {0}'.format(mg.text)


@app.route('/execute/<script_slug>')
def endpoint(script_slug):
    output = []
    returncode = None
    script_output = None
    os_errors = []
    subprocess_errors = []

    check_setting_sanity()

    print 'sanity passed'

    # Check host
    if not settings.ALLOWED_HOSTS_ALL:
        if request.remote_addr not in settings.ALLOWED_HOSTS:
            raise UnallowedHostException('You are calling from: %s which is not allowed.' % request.remote_addr)

    # Check API Key
    if request.args.get('api_key') not in settings.API_KEYS:
        raise APIKeyException('Your API Key is invalid or missing.')

    # Load our script
    script = settings.SCRIPTS.get(script_slug)

    # Check is that script is actually valid
    if not script:
        raise UnknownScriptException('You are requesting a script that is not defined in SCRIPTS.')

    try:
        script_output = subprocess.check_output(script['executable'], stderr=subprocess.STDOUT)

    except OSError as e:
        os_errors.append(e)
        returncode = 0

    except subprocess.CalledProcessError as e:
        returncode = e.returncode
        subprocess_errors.append(e.output)

    if script_output:
        output.append(script_output)

    print "== RESULT =="
    print "RETURN_CODE: %s" % returncode
    print "OUTPUT: %s" % output
    print "OS_ERRORS: %s" % os_errors
    print "SUBPROCESS_ERRORS: %s" % subprocess_errors

    send_mail(script, output, returncode, os_errors, subprocess_errors)

    return "complete"


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

