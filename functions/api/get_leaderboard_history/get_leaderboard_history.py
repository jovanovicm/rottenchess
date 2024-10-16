import boto3
import os
import json
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
    LEADERBOARD_HISTORY_TABLE = os.getenv('LEADERBOARD_HISTORY_TABLE')
    dynamodb = boto3.resource('dynamodb')
    leaderboard_table = dynamodb.Table(LEADERBOARD_HISTORY_TABLE)

    query_params = event.get('queryStringParameters', {})
    year = query_params.get('year')
    month = query_params.get('month')

    if not year or not month:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing query parameter: year or month'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

    date = f"{year}/{month}"

    response = leaderboard_table.get_item(
        Key={'date': date}
    )
    
    if 'Item' in response:
        item = convert_decimals(response['Item'])
        return {
            'statusCode': 200,
            'body': json.dumps(item),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'No leaderboard data found for the specified date'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }