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
    table = dynamodb.Table(PLAYER_STATS_TABLE)

    query_params = event.get('queryStringParameters', {})
    
    if query_params.get('batch') == 'true':
        body = json.loads(event['body'])
        usernames = body['usernames']
        
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
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    
    username = query_params.get('username')
    if username:
        response = table.get_item(Key={'username': username})

        if 'Item' in response:
            item = convert_decimals(response['Item'])
            return {
                'statusCode': 200,
                'body': json.dumps(item),
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Player not found'}),
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
    
    return {
        'statusCode': 400,
        'body': json.dumps({'error': 'Invalid request'}),
        'headers': {
            'Content-Type': 'application/json'
        }
    }