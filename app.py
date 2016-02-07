from flask import Flask
from flask import request
import subprocess

from utils import *

app = Flask(__name__)
app.config.from_pyfile('config.py')


@app.route('/')
def landing():
    return "This is bmx."


@app.route('/execute/<script_slug>', methods=['GET', 'POST'])
def execute(script_slug):
    output = []
    return_code = None
    script_output = None
    os_errors = []
    bmx_errors = []
    subprocess_errors = []
    result = ""
    sanity_passed = False
    security_passed = False
    script = None

    if request.args.get('actor'):
        # Looks like a call from BitBucket
        actor = request.args.get('actor').get('display_name')
        repo = request.args.get('repository').get('name')
        link = request.args.get('push').get('changes').get('links').get('html')

        print "actor: %s" % actor
        print "repo: %s" % repo
        print "link: %s" % link

    try:
        check_setting_sanity()
        sanity_passed = True
    except (AllowedHostsOverlapException, DefaultAPIKeyStillConfiguredException,) as e:
        bmx_errors.append('Sanity failure: %s' % e.message)
        result = e.message

    try:
        script = check_security(request, script_slug)
        security_passed = True

    except (UnallowedHostException, APIKeyException, UnknownScriptException) as e:
        bmx_errors.append('Security failure: %s' % e.message)
        result = e.message

    if script and sanity_passed and security_passed:
        # Run the script
        try:
            script_output = subprocess.check_output(script['executable'], stderr=subprocess.STDOUT)
            result = "Script executed successfully"
            return_code = 0

        except OSError as e:
            os_errors.append(str(e))
            return_code = 0
            result = "Script executed with errors"

        except subprocess.CalledProcessError as e:
            return_code = e.returncode
            subprocess_errors.append(e.output)
            result = "Script executed with errors"

        if script_output:
            output.append(script_output)

    send_mail(script, output, return_code, os_errors, subprocess_errors, bmx_errors, result)

    if script is None:
        result = "Invalid Script"

    return result


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

