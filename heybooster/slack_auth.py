from database import db
import json

import logging
import flask
from flask import request, url_for, redirect, current_app
from flask_dance.consumer import oauth_authorized, oauth_error
from werkzeug.wrappers import Response
from oauthlib.oauth2 import MissingCodeError

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
        print("aDADADAD")
        token = self.session.fetch_token(
            self.token_url,
            authorization_response=request.url,
            client_secret=self.client_secret,
            **self.token_url_params
        )
        db.find_and_modify(collection='user', email=flask.session['email'], sl_accesstoken=token['access_token'])
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
    return redirect(next_url)
