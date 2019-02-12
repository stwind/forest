from uuid import uuid4
from datetime import datetime

import boto3

FMT_TIME = '%Y-%m-%dT%H:%M:%SZ'


def ftime(dt, fmt=FMT_TIME):
    return dt.strftime(fmt)


def ptime(dt, fmt=FMT_TIME):
    return datetime.strptime(dt, fmt)


def create_poll(table, poll):
    now = ftime(datetime.now())
    poll['created_at'] = now
    poll['updated_at'] = now
    poll['options'] = poll.get('options', {})
    poll['votes'] = poll.get('votes', {})
    table.put_item(Item=poll)


def get_poll(table, message_ts):
    response = table.get_item(Key={'message_ts': message_ts})
    return response['Item'] if 'Item' in response else None


def add_option(table, message_ts, option):
    now = ftime(datetime.now())
    option['created_at'] = ftime(datetime.now())
    id_ = str(uuid4())
    table.update_item(
        Key={'message_ts': message_ts},
        UpdateExpression='SET options.#id = :option, updated_at = :updated_at',
        ExpressionAttributeNames={'#id': id_},
        ExpressionAttributeValues={':option': option, ':updated_at': now},
    )
    return id_


def vote(table, message_ts, user, option_id):
    now = ftime(datetime.now())
    table.update_item(
        Key={'message_ts': message_ts},
        UpdateExpression='SET votes.#user = :option_id, updated_at = :updated_at',
        ExpressionAttributeNames={'#user': user},
        ExpressionAttributeValues={':option_id': option_id, ':updated_at': now},
    )


def get_votes_result(table, poll):
    n_res = {}
    for u, o in poll['votes'].items():
        n_res[o] = n_res.get(o, 0) + 1

    result = []
    for o, n in n_res.items():
        result.append((poll['options'][o]['value'], n))

    return sorted(result, key=lambda v: v[1], reverse=True)
