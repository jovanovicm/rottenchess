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
    print("Received event:", json.dumps(event))

    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PLAYER_STATS_TABLE)

    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    # Extract path parameters
    path_params = event.get('pathParameters') or {}
    username = path_params.get('username')

    if username:
        # Handle single player retrieval
        response = table.get_item(Key={'username': username})
        if 'Item' in response:
            item = convert_decimals(response['Item'])
            return {
                'statusCode': 200,
                'body': json.dumps(item),
                'headers': headers
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Player not found'}),
                'headers': headers
            }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Username is required'}),
            'headers': headers
        }