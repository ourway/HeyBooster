from database import db
import json
from datetime import datetime, timedelta, timezone
import logging
import flask
from flask import request, url_for, redirect, current_app
from flask_dance.consumer import oauth_authorized, oauth_error
from werkzeug.wrappers import Response
from oauthlib.oauth2 import MissingCodeError
import requests
import google_auth

URL = "https://slack.com/api/{}"
log = logging.getLogger(__name__)



def authorized(self):
    """
    This is the route/function that the user will be redirected to by
    the provider (e.g. Twitter) after the user has logged into the
    provider's website and authorized your app to access their account.
    """
    if self.redirect_url:
        next_url = self.redirect_url
    elif self.redirect_to:
        next_url = url_for(self.redirect_to)
    else:
        next_url = "/"
    log.debug("next_url = %s", next_url)

    # check for error in request args
    error = request.args.get("error")
    if error:
        error_desc = request.args.get("error_description")
        error_uri = request.args.get("error_uri")
        log.warning(
            "OAuth 2 authorization error: %s description: %s uri: %s",
            error,
            error_desc,
            error_uri,
        )
        oauth_error.send(
            self, error=error, error_description=error_desc, error_uri=error_uri
        )
        return redirect(next_url)

    state_key = "{bp.name}_oauth_state".format(bp=self)
    if state_key not in flask.session:
        # can't validate state, so redirect back to login view
        log.info("state not found, redirecting user to login")
        return redirect(url_for(".login"))

    state = flask.session[state_key]
    log.debug("state = %s", state)
    self.session._state = state
    del flask.session[state_key]

    self.session.redirect_uri = url_for(".authorized", _external=True)

    log.debug("client_id = %s", self.client_id)
    log.debug("client_secret = %s", self.client_secret)
    try:
        token = self.session.fetch_token(
            self.token_url,
            authorization_response=request.url,
            client_secret=self.client_secret,
            **self.token_url_params
        )
        db.find_and_modify(collection='user', query={'email': google_auth.get_user_info()['email']},
                           sl_accesstoken=token['access_token'], sl_userid=token['user_id'])
    except MissingCodeError as e:
        e.args = (
            e.args[0],
            "The redirect request did not contain the expected parameters. Instead I got: {}".format(
                json.dumps(request.args)
            ),
        )
        raise

    results = oauth_authorized.send(self, token=token) or []
    set_token = True
    for func, ret in results:
        if isinstance(ret, (Response, current_app.response_class)):
            return ret
        if ret == False:
            set_token = False

    if set_token:
        try:
            self.token = token

        except ValueError as error:
            log.warning("OAuth 2 authorization error: %s", str(error))
            oauth_error.send(self, error=error)
            
#    # When the slack connection is completed send notification user to set time
#    headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + token['access_token']}
#    data = {
#        "channel": token['incoming_webhook']['channel'],
#        "attachments": [{
#            "text": """Hi, I am HeyBooster, Default notification time is set as 07:00.
#Click "Change" button for changing it.""",
#            "title": "Blog Yazıları",
#            "title_link": "https://blog.boostroas.com/tr/"},
#            {
#                "text": "",
#                "callback_id": "notification_form",
#                "color": "#3AA3E3",
#                "attachment_type": "default",
#                "actions": [
#                    {
#                        "name": "change",
#                        "text": "Change",
#                        "type": "button",
#                        "value": "change"
#                    }]
#            }]}
#    requests.post(URL.format('chat.postMessage'), data=json.dumps(data), headers=headers)
#    modules = db.find("notification", query={'email': google_auth.get_user_info()['email']})
#    lc_tz_offset = datetime.now(timezone.utc).astimezone().utcoffset().seconds // 3600
#    #    usr_tz_offset = self.post("users.info", data={'user':token['user_id']})['user']['tz_offset']
#    data = [('token', token['access_token']),
#            ('user', token['user_id'])]
#    usr_tz_offset = requests.post(URL.format('users.info'), data).json()['user']['tz_offset'] // 3600
#    if (7 >= (usr_tz_offset - lc_tz_offset)):
#        default_time = str(7 - (usr_tz_offset - lc_tz_offset)).zfill(2)
#    else:
#        default_time = str(24 + (7 - (usr_tz_offset - lc_tz_offset))).zfill(2)
#    for module in modules:
#        db.find_and_modify("notification", query={'_id': module['_id']}, timeofDay="%s.00" % (default_time))
            
    return redirect(next_url)
