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

    allowed_origins = [
        'https://rottenchess.com',
        'https://www.rottenchess.com',
        'http://localhost:3000'
    ]

    origin = event['headers'].get('origin')
    if origin in allowed_origins:
        access_control_allow_origin = origin
    else:
        access_control_allow_origin = 'null'

    path_params = event.get('pathParameters', {})
    username = path_params.get('username')

    if username == 'batch':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': access_control_allow_origin,
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
            }
        }
    
    if not username:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Username is required'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': access_control_allow_origin,
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
            }
        }

    response = table.get_item(Key={'username': username})

    if 'Item' in response:
        item = convert_decimals(response['Item'])
        return {
            'statusCode': 200,
            'body': json.dumps(item),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': access_control_allow_origin,
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
            }
        }
    
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Player not found'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': access_control_allow_origin,
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
            }
        }