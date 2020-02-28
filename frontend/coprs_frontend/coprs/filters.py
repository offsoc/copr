import datetime
from six.moves.urllib.parse import urlparse
import pytz
import time

try:
    import commonmark
except:
    # needed for Fedora <= 29
    import CommonMark as commonmark

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound
from pygments.formatters import HtmlFormatter

import humanize
import os
import re

from flask import Markup, url_for

from copr_common.enums import ModuleStatusEnum, StatusEnum
from coprs import app
from coprs import helpers

class CoprHtmlRenderer(commonmark.HtmlRenderer):
    def code_block(self, node, entering):
        info_words = node.info.split() if node.info else []
        attrs = self.attrs(node)
        lexer = None

        if len(info_words) > 0 and len(info_words[0]) > 0:
            try:
                code = commonmark.common.escape_xml(info_words[0])
            except TypeError:
                # fallback for Fedora <= 30
                code = commonmark.common.escape_xml(info_words[0], True)
            attrs.append(['class', 'language-' + code])

            try:
                lexer = get_lexer_by_name(info_words[0])
            except ClassNotFound:
                pass

        if lexer is None:
            try:
                lexer = guess_lexer(node.literal)
            except ClassNotFound:
                lexer = TextLexer

        self.cr()
        self.tag('pre')
        self.tag('code', attrs)
        code = highlight(node.literal, lexer, HtmlFormatter())
        code = re.sub('<pre>', '', code)
        code = re.sub('</pre>', '', code)
        self.lit(code)
        self.tag('/code')
        self.tag('/pre')
        self.cr()


@app.template_filter("remove_anchor")
def remove_anchor(data):
    if data:
        data = re.sub("<.*?>", "", data)
        data = re.sub("</a>", "", data)
        return data
    return None

@app.template_filter("date_from_secs")
def date_from_secs(secs):
    if secs:
        return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.gmtime(secs))

    return None


@app.template_filter("perm_type_from_num")
def perm_type_from_num(num):
    return helpers.PermissionEnum(num)


@app.template_filter("state_from_num")
def state_from_num(num):
    if num is None:
        return "unknown"
    return StatusEnum(num)


@app.template_filter("module_state_from_num")
def module_state_from_num(num):
    if num is None:
        return "unknown"
    return ModuleStatusEnum(num)


@app.template_filter("os_name_short")
def os_name_short(os_name, os_version):
    # TODO: make it models.MockChroot method or not?
    if os_version:
        if os_version == "rawhide":
            return os_version
        if os_name == "fedora":
            return "fc.{0}".format(os_version)
        elif os_name == "epel":
            return "el{0}".format(os_version)
    return os_name


@app.template_filter('localized_time')
def localized_time(time_in, timezone):
    """ return time shifted into timezone (and printed in ISO format)

    Input is in EPOCH (seconds since epoch).
    """
    if not time_in:
        return "Not yet"
    format_tz = "%Y-%m-%d %H:%M %Z"
    utc_tz = pytz.timezone('UTC')
    if timezone:
        user_tz = pytz.timezone(timezone)
    else:
        user_tz = utc_tz
    dt_aware = datetime.datetime.fromtimestamp(time_in).replace(tzinfo=utc_tz)
    dt_my_tz = dt_aware.astimezone(user_tz)
    return dt_my_tz.strftime(format_tz)


@app.template_filter('timestamp_diff')
def timestamp_diff(time_in, until=None):
    """ returns string with difference between two timestamps

    Input is in EPOCH (seconds since epoch).
    """
    if time_in is None:
        return " - "
    if until is not None:
        now = datetime.datetime.fromtimestamp(until)
    else:
        now = datetime.datetime.now()
    diff = now - datetime.datetime.fromtimestamp(time_in)
    return str(int(diff.total_seconds()))


@app.template_filter('time_ago')
def time_ago(time_in, until=None):
    """ returns string saying how long ago the time on input was

    Input is in EPOCH (seconds since epoch).
    """
    if time_in is None:
        return " - "
    if until is not None:
        now = datetime.datetime.fromtimestamp(until)
    else:
        now = datetime.datetime.now()
    diff = now - datetime.datetime.fromtimestamp(time_in)
    return humanize.naturaldelta(diff)


@app.template_filter("markdown")
def markdown_filter(data):
    if not data:
        return ''

    parser = commonmark.Parser()
    renderer = CoprHtmlRenderer()

    return Markup(renderer.render(parser.parse(data)))


@app.template_filter("pkg_name")
def parse_package_name(pkg):
    if pkg is not None:
        return helpers.parse_package_name(os.path.basename(pkg))
    return pkg


@app.template_filter("basename")
def parse_basename(pkg):
    if pkg is not None:
        return os.path.basename(pkg)
    return pkg


@app.template_filter("build_state_description")
def build_state_decoration(state):

    description_map = {
        "failed": "Build failed. See logs for more details.",
        "succeeded": "Successfully built.",
        "canceled": "The build has been cancelled manually.",
        "running": "Build in progress.",
        "pending": "Your build is waiting for a builder.",
        "skipped": "This package has already been built previously.",
        "starting": "Trying to acquire and configure builder for task.",
        "importing": "Package content is being imported into DistGit.",
        "waiting": "Task is waiting for something else to finish.",
        "imported": "Package was successfully imported into DistGit.",
        "forked": "Build has been forked from another build.",
    }

    return description_map.get(state, "")


@app.template_filter("build_source_description")
def build_source_description(state):
    description_map = {
        "unset": "No default source",
        "link": "External link to .spec or SRPM",
        "upload": "SRPM or .spec file upload",
        "scm": "Build from an SCM repository",
        "pypi": "Build from PyPI",
        "rubygems": "Build from RubyGems",
        "custom": "Custom build method",
    }

    return description_map.get(state, "")


@app.template_filter("fix_url_https_backend")
def fix_url_https_backend(url):
    if app.config.get('REPO_NO_SSL', False):
        return url.replace('https://', 'http://')
    return helpers.fix_protocol_for_backend(url)


@app.template_filter("fix_url_https_frontend")
def fix_url_https_frontend(url):
    return helpers.fix_protocol_for_frontend(url)

@app.template_filter("repo_url")
def repo_url(url):
    """
    render copr://<user>/<prj> or copr://g/<group>/<prj>
    to be rendered as copr projects pages
    """
    parsed = urlparse(url)
    if parsed.scheme == "copr":
        owner = parsed.netloc
        prj = parsed.path.split("/")[1]
        if owner[0] == '@':
            url = url_for("coprs_ns.copr_detail", group_name=owner[1:], coprname=prj)
        else:
            url = url_for("coprs_ns.copr_detail", username=owner, coprname=prj)

    return helpers.fix_protocol_for_frontend(url)

@app.template_filter("mailto")
def mailto(url):
    return url if urlparse(url).scheme else "mailto:{}".format(url)
