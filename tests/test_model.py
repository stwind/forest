import pytest
import boto3
from uuid import uuid4
from datetime import datetime
from moto import mock_dynamodb2

from forest.models import (
    create_poll, get_poll, add_option, vote, get_votes_result
)


TABLES = {
    'polls': {
        'KeySchema': [{'AttributeName': 'message_ts', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [{'AttributeName': 'message_ts', 'AttributeType': 'S'}],
        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    }
}


@pytest.fixture
def dynamodb():
    with mock_dynamodb2():
        yield boto3.resource('dynamodb')


@pytest.fixture
def tables(dynamodb):
    tbls = {}
    for name, defs in TABLES.items():
        table = dynamodb.create_table(
            TableName=name,
            KeySchema=defs['KeySchema'],
            AttributeDefinitions=defs['AttributeDefinitions'],
            ProvisionedThroughput=defs['ProvisionedThroughput'])
        table.meta.client.get_waiter('table_exists').wait(TableName=name)
        tbls[name] = table

    yield tbls

    for name, table in tbls.items():
        table.delete()

def test_poll(tables):
    table = tables['polls']

    msg_ts = 'msg_ts'
    poll = {'title': 'test',
            'team': 'team_id',
            'user': 'user_id',
            'channel': 'channel_id',
            'message_ts': msg_ts}
    create_poll(table, poll)
    item = get_poll(table, msg_ts)
    assert item['title'] == poll['title']
    assert item['team'] == poll['team']
    assert item['user'] == poll['user']
    assert item['channel'] == poll['channel']

    opt_id = add_option(table, msg_ts, {'value': 'opt1', 'creator': 'user1'})
    item = get_poll(table, msg_ts)
    assert item['options'][opt_id]['value'] == 'opt1'

    vote(table, msg_ts, 'user1', opt_id)
    item = get_poll(table, msg_ts)
    assert item['votes']['user1'] == opt_id

    opt_id2 = add_option(table, msg_ts, {'value': 'opt2', 'creator': 'user1'})
    vote(table, msg_ts, 'user1', opt_id2)
    item = get_poll(table, msg_ts)
    assert item['votes']['user1'] == opt_id2

    vote(table, msg_ts, 'user2', opt_id)
    vote(table, msg_ts, 'user3', opt_id)

    result = get_votes_result(table, get_poll(table, msg_ts))
    assert result[0] == ('opt1', 2)
    assert result[1] == ('opt2', 1)
