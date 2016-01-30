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


def check_security(request, script_slug):
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

    return script


def build_html_output(script, output, returncode, os_errors, subprocess_errors, bmx_errors, result):
    out = "<table>"

    out += "<tr><td><strong>Script</strong></td><td>%s</td></tr>" % script['executable']
    out += "<tr><td><strong>Result</strong></td><td>%s</td></tr>" % result
    out += "<tr><td><strong>Return Code</strong></td><td>%s</td></tr>" % returncode
    out += "<tr><td><strong>Output</strong></td><td>%s</td></tr>" % output
    out += "<tr><td><strong>OS Errors</strong></td><td>%s</td></tr>" % os_errors
    out += "<tr><td><strong>Subprocess Errors</strong></td><td>%s</td></tr>" % subprocess_errors
    out += "<tr><td><strong>BMX Errors</strong></td><td>%s</td></tr>" % bmx_errors
    out += "</table>"

    return out


def send_mail(script, output, returncode, os_errors, subprocess_errors, bmx_errors, result):
    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(settings.MAILGUN_SANDBOX)
    html = build_html_output(script, output, returncode, os_errors, subprocess_errors, bmx_errors, result)

    for email in script['email']:
        mg = requests.post(request_url, auth=('api', settings.MAILGUN_KEY), data={
            'from': settings.MAILGUN_FROM_ADDRESS,
            'to': email,
            'subject': 'BMX: %s ' % result,
            'html': html
        })


@app.route('/execute/<script_slug>')
def endpoint(script_slug):
    output = []
    returncode = None
    script_output = None
    os_errors = []
    bmx_errors = []
    subprocess_errors = []
    result = ""
    sanity_passed = False
    security_passed = False


    try:
        check_setting_sanity()
        sanity_passed = True
    except (AllowedHostsOverlapException, DefaultAPIKeyStillConfiguredException,) as e:
        bmx_errors.append('Sanity failure: %s' % e.message)

    try:
        script = check_security(request, script_slug)
        security_passed = True

    except (UnallowedHostException, APIKeyException, UnknownScriptException) as e:
        bmx_errors.append('Security failure: %s' % e.message)

    if sanity_passed and security_passed:
        # Run the script
        try:
            script_output = subprocess.check_output(script['executable'], stderr=subprocess.STDOUT)
            result = "SUCCESS"

        except OSError as e:
            os_errors.append(e)
            returncode = 0
            result = "SUCCESS WITH ERRORS"

        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            subprocess_errors.append(e.output)
            result = "SUCCESS WITH ERRORS"

        if script_output:
            output.append(script_output)

    send_mail(script, output, returncode, os_errors, subprocess_errors, bmx_errors, result)

    return result


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

