"""
Authentication-related code for communication with FAS, Kerberos, LDAP, etc.
"""

from urllib.parse import urlparse
import flask
from openid_teams.teams import TeamsRequest
from coprs import oid
from coprs import app
from coprs.exceptions import CoprHttpException
from coprs.logic.users_logic import UsersLogic


class FedoraAccounts:
    """
    Authentication via user accounts from
    https://accounts.fedoraproject.org
    """

    @classmethod
    def username(cls):
        """
        Is a user logged-in? Return their username
        """
        if "openid" in flask.session:
            return cls.fed_raw_name(flask.session["openid"])
        return None

    @staticmethod
    def login():
        """
        If not already logged-in, perform a log-in request
        """
        if flask.g.user is not None:
            return flask.redirect(oid.get_next_url())

        # If the login is successful, we are redirected to function decorated
        # with the `@oid.after_login`
        team_req = TeamsRequest(["_FAS_ALL_GROUPS_"])
        return oid.try_login(app.config["OPENID_PROVIDER_URL"],
                            ask_for=["email", "timezone"],
                            extensions=[team_req])

    @staticmethod
    def logout():
        """
        Log out the current user
        """
        flask.session.pop("openid", None)

    @staticmethod
    def is_user_allowed(username):
        """
        Is this user allowed to log in?
        """
        if not username:
            return False
        if not app.config["USE_ALLOWED_USERS"]:
            return True
        return username in app.config["ALLOWED_USERS"]

    @staticmethod
    def fed_raw_name(oidname):
        """
        Convert the full `oidname` to username
        """
        oidname_parse = urlparse(oidname)
        if not oidname_parse.netloc:
            return oidname
        config_parse = urlparse(app.config["OPENID_PROVIDER_URL"])
        return oidname_parse.netloc.replace(".{0}".format(config_parse.netloc), "")

    @classmethod
    def user_from_response(cls, resp):
        """
        Create a `models.User` object from FAS response
        """
        username = cls.fed_raw_name(resp.identity_url)
        user = UsersLogic.get(username).first()

        # Create if not created already
        if not user:
            app.logger.info("First login for user '%s', "
                            "creating a database record", username)
            user = UsersLogic.create_user_wrapper(username, resp.email, resp.timezone)

        # Update user attributes from FAS
        user.mail = resp.email
        user.timezone = resp.timezone
        return user

    @staticmethod
    def groups_from_response(resp):
        """
        Return a list of group names (that a user belongs to) from FAS response
        """
        if "lp" in resp.extensions:
            # name space for the teams extension
            team_resp = resp.extensions['lp']
            return {"fas_groups": team_resp.teams}
        return None


class Kerberos:
    """
    Authentication via Kerberos / GSSAPI
    """

    @staticmethod
    def username():
        """
        Is a user logged-in? Return their username
        """
        if "krb5_login" in flask.session:
            return flask.session["krb5_login"]
        return None

    @classmethod
    def login(cls):
        """
        If not already logged-in, perform a log-in request
        """
        return cls._krb5_login_redirect(next_url=oid.get_next_url())

    @staticmethod
    def logout():
        """
        Log out the current user
        """
        flask.session.pop("krb5_login", None)

    @staticmethod
    def user_from_username(username):
        """
        Create a `models.User` object from Kerberos username
        """
        user = UsersLogic.get(username).first()
        if user:
            return user

        # We can not create a new user now because we don't have the necessary
        # e-mail and groups info.
        if app.config["FAS_LOGIN"] is True:
            return None

        # Create a new user object
        krb_config = app.config['KRB5_LOGIN']
        email = username + "@" + krb_config['email_domain']
        return UsersLogic.create_user_wrapper(username, email)

    @staticmethod
    def _krb5_login_redirect(next_url=None):
        if app.config['KRB5_LOGIN']:
            # Pick the first one for now.
            return flask.redirect(flask.url_for("apiv3_ns.krb5_login",
                                                next=next_url))
        flask.flash("Unable to pick krb5 login page", "error")
        return flask.redirect(flask.url_for("coprs_ns.coprs_show"))