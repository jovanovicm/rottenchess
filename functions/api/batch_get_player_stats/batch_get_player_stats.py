import json
import boto3
import os
from decimal import Decimal

def convert_decimals(item):
    if isinstance(item, list):
        return [convert_decimals(i) for i in item]
    elif isinstance(item, dict):
        return {k: convert_decimals(v) for k, v in item.items()}
    elif isinstance(item, Decimal):
        return int(item)
    else:
        return item

def lambda_handler(event, context):
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    dynamodb = boto3.resource('dynamodb')

    body = json.loads(event['body'])
    usernames = body.get('usernames', [])

    if not usernames:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Usernames are required'}),
            'headers': {'Content-Type': 'application/json'}
        }

    keys = [{'username': username} for username in usernames]
    response = dynamodb.batch_get_item(
        RequestItems={
            PLAYER_STATS_TABLE: {
                'Keys': keys
            }
        }
    )
    items = response['Responses'].get(PLAYER_STATS_TABLE, [])
    converted_items = [convert_decimals(item) for item in items]

    return {
        'statusCode': 200,
        'body': json.dumps(converted_items),
        'headers': {'Content-Type': 'application/json'}
    }