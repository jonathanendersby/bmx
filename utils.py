import requests

import settings
from exceptions import *


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


def to_friendly(in_list):
    out = ''.join(in_list)
    out = out.replace('\n','<br />')
    return out


def build_html_output(script, output, return_code, os_errors, subprocess_errors, bmx_errors, result):

    output = ''.join(output).replace("\n", "<br />")

    td1_pre = "<tr><td style='border:1px solid #7A7A7A; vertical-align:top; padding-bottom:10px; padding-top:10px; " \
              "padding-left:5px; padding-right:10px;'><strong>"
    td1_pst = "<strong></td>"
    td2_pre = "<td style='border:1px solid #7A7A7A; padding-left:10px; padding-bottom:10px; padding-right:10px; " \
              "padding-top:10px;'>"
    td2_pst = "</td></tr>"

    out = "<table style='border:1px solid #7A7A7A; border-collapse:collapse;'>"
    out += "%s Script %s %s %s %s" % (td1_pre, td1_pst, td2_pre, script['executable'], td2_pst)
    out += "%s Result %s %s %s %s" % (td1_pre, td1_pst, td2_pre, result, td2_pst)
    out += "%s Return Code %s %s %s %s" % (td1_pre, td1_pst, td2_pre, return_code, td2_pst)
    out += "%s Output %s %s %s %s" % (td1_pre, td1_pst, td2_pre, output, td2_pst)
    out += "%s Subprocess Errors %s %s %s %s" % (td1_pre, td1_pst, td2_pre, to_friendly(subprocess_errors), td2_pst)
    out += "%s OS Errors %s %s %s %s" % (td1_pre, td1_pst, td2_pre, to_friendly(os_errors), td2_pst)
    out += "%s BMX Errors %s %s %s %s" % (td1_pre, td1_pst, td2_pre, to_friendly(bmx_errors), td2_pst)
    out += "</table>"

    return out


def send_mail(script, output, return_code, os_errors, subprocess_errors, bmx_errors, result):
    request_url = 'https://api.mailgun.net/v2/{0}/messages'.format(settings.MAILGUN_SANDBOX)
    html = build_html_output(script, output, return_code, os_errors, subprocess_errors, bmx_errors, result)

    for email in script['email']:
        mg = requests.post(request_url, auth=('api', settings.MAILGUN_KEY), data={
            'from': settings.MAILGUN_FROM_ADDRESS,
            'to': email,
            'subject': result,
            'html': html
        })
