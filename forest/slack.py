import os
import hmac
import hashlib
import json
from time import time
from datetime import datetime
from functools import wraps

from slackclient import SlackClient

from forest.api import response


def hmac_signature(timestamp, body):
    message = "v0:{}:{}".format(timestamp, body)
    return 'v0=' + hmac.new(str.encode(os.environ['SLACK_API_SIGNING_SECRET']),
                            str.encode(message),
                            hashlib.sha256).hexdigest()


def is_valid_request(req):
    if "X-Slack-Request-Timestamp" not in req["headers"] or \
       "X-Slack-Signature" not in req["headers"]:
        return False

    req_ts = int(req["headers"]["X-Slack-Request-Timestamp"])
    now_ts = int(datetime.now().timestamp())
    if abs(req_ts - now_ts) > (60 * 5):
        return False

    expected = hmac_signature(req_ts, req['body'])
    actual = req["headers"]["X-Slack-Signature"]
    return hmac.compare_digest(expected, actual)


def verify_request(func):
    @wraps(func)
    def wrapper(req, ctx):
        if not is_valid_request(req):
            return response(403, {'Content-Type': 'text/plain'}, 'Invalid Requset')
        return func(req, ctx)

    return wrapper


def connect(token=os.environ['SLACK_API_TOKEN']):
    return SlackClient(token)


def dialog_open(sc, dialog, trigger_id):
    return sc.api_call('dialog.open', dialog=json.dumps(dialog), trigger_id=trigger_id)


def post_message(sc, channel, text, attachments=[], username=os.environ['SLACK_BOT_NAME']):
    return sc.api_call('chat.postMessage',
                       channel=channel,
                       text=text,
                       attachments=attachments,
                       as_user=not bool(username),
                       username=username)


def chat_upate(sc, channel, text, ts, attachments=[]):
    return sc.api_call('chat.update', channel=channel, text=text, ts=ts, attachments=attachments)


def chat_getpermalink(sc, channel, ts):
    res = sc.api_call('chat.getPermalink', channel=channel, message_ts=ts)
    return res['permalink'] if res['ok'] else None


def conversations_history(sc, channel, limit=20):
    res = sc.api_call('conversations.history', channel=channel, limit=limit)
    return res['messages'] if res['ok'] else None
