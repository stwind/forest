import json
import logging
import os
import sys
import boto3
from functools import reduce
from uuid import uuid4
from urllib.parse import parse_qs
from datetime import datetime
from boltons.iterutils import chunked

from forest.api import response
from forest.slack import (
    verify_request, connect, dialog_open, post_message, chat_upate, chat_getpermalink
)
from forest.models import (
    ftime, create_poll, get_poll, add_option, vote, get_votes_result
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@verify_request
def command_ping(req, ctx):
    text = parse_qs(req['body'])['text'][0]
    return response(200, {'Content-Type': 'text/plain'}, 'pong: {}'.format(text))


@verify_request
def command_poll(req, ctx):
    payload = parse_qs(req['body'])
    title = payload['text'][0]
    trigger_id = payload['trigger_id'][0]

    sc = connect()
    dialog = {"callback_id": "create_poll",
              "title": title, "state": title,
              "elements": [{"type": "text",
                            "label": "Option 1",
                            "name": str(uuid4())},
                           {"type": "text",
                            "label": "Option 2",
                            "name": str(uuid4())}]}

    dialog_open(sc, dialog, trigger_id)
    return response(200, {'Content-Type': 'text/plain'}, None)


def acc_field(acc, r, total):
    acc.append({'title': r[0],
                'value': '▇' * r[1] + ' ({})'.format(r[1]),
                'short': False})
    return acc


def new_option_action():
    return {'name': 'new_option', 'text': '+',
            'type': 'button', 'value': 'other'}


def update_vote_message(table, sc, poll):
    result = get_votes_result(table, poll)
    total = sum(r[1] for r in result)
    fields = reduce(lambda a, r: acc_field(a, r, total), result, [])

    attachments = []

    for opts in chunked(poll['options'].items(), 5):
        actions = [{'name': o['value'],
                    'text': o['value'],
                    'type': 'button',
                    'value': id_}
                   for (id_, o) in opts]
        if len(actions) < 5:
            actions.append(new_option_action())
        attachments.append({
            "text": '',
            "fallback": "error",
            "callback_id": "vote",
            "actions": actions
        })

    if attachments[-1]['actions'][-1]['name'] != 'new_option':
        attachments.append({"text": '',
                            "fallback": "error",
                            "callback_id": "vote",
                            "actions": [new_option_action()]})

    attachments.append({'fields': fields})

    chat_upate(sc, poll['channel'], poll['title'], poll['message_ts'], attachments=attachments)


def notify_new_option(sc, poll, option):
    text = '> {}\n有了新选项 *{}*\n{}'.format(poll['title'], option['value'], poll['permalink'])
    post_message(sc, poll['channel'], text)


def notify_new_result(sc, old, new, poll):
    if len(old) > 0 and old[0][0] != new[0][0]:
        text = '> {}\n有了新结果 *{}*\n{}'.format(poll['title'], new[0][0], poll['permalink'])
        post_message(sc, poll['channel'], text)


@verify_request
def actions(req, ctx):
    payload = json.loads(parse_qs(req['body'])['payload'][0])
    logger.debug(payload)

    sc = connect()
    table = boto3.resource('dynamodb').Table(os.environ['TABLE_POLLS'])

    if payload['type'] == 'dialog_submission':
        if payload['callback_id'] == 'create_poll':
            title = payload['state']
            submission = payload['submission']
            actions = [{'name': v, 'text': v, 'type': 'button', 'value': k}
                       for k, v in submission.items()]
            actions.append(new_option_action())
            attachments = [{"text": '', "fallback": "error",
                            "callback_id": "vote", "actions": actions}]
            res = post_message(sc, payload['channel']['id'], title, attachments=attachments)
            pl = chat_getpermalink(sc, payload['channel']['id'], res['message']['ts'])
            poll = {'title': title,
                    'team': payload['team']['id'],
                    'user': payload['user']['id'],
                    'channel': payload['channel']['id'],
                    'options': {k: {'value': v, 'creator': payload['user']['id'],
                                    'created_at': ftime(datetime.now())}
                                for k, v in submission.items()},
                    'permalink': pl,
                    'message_ts': res['message']['ts']}
            create_poll(table, poll)

        elif payload['callback_id'] == 'add_option':
            msg_ts = payload['state']
            poll = get_poll(table, msg_ts)
            if poll:
                v, n = list(payload['submission'].items())[0]
                logger.info('Added option {} to poll {}'.format(v, msg_ts))
                option = {'value': n, 'creator': payload['user']['id']}
                add_option(table, msg_ts, option)

                poll1 = get_poll(table, msg_ts)
                update_vote_message(table, sc, poll1)
                notify_new_option(sc, poll1, option)

    elif payload['type'] == 'interactive_message':
        if payload['callback_id'] == 'vote':
            msg_ts = payload['message_ts']
            poll = get_poll(table, msg_ts)
            if poll:
                action = payload['actions'][0]
                if action['name'] == 'new_option':
                    dialog = {"callback_id": "add_option",
                              "title": poll['title'],
                              "state": msg_ts,
                              "elements": [{"type": "text", "label": "New Option", "name": "value"}]}
                    logger.info('Adding option to poll {}'.format(msg_ts))
                    dialog_open(sc, dialog, payload['trigger_id'])
                else:
                    opt_id = action['value']
                    channel = payload['channel']['id']
                    user = payload['user']['id']
                    logger.info('{} in {} voted {} for {}'.format(user, channel, opt_id, msg_ts))

                    vote(table, msg_ts, user, opt_id)
                    poll1 = get_poll(table, msg_ts)

                    update_vote_message(table, sc, poll1)

                    notify_new_result(sc,
                                      get_votes_result(table, poll),
                                      get_votes_result(table, poll1),
                                      poll1)

    return response(200, {'Content-Type': 'text/plain'}, None)
