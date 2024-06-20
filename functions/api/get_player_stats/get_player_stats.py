import json
import boto3
import os

def lambda_handler(event, context):
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PLAYER_STATS_TABLE)
    username = event['pathParameters']['username']
    
    response = table.get_item(Key={'username': username})
    
    if 'Item' in response:
        return {
            'statusCode': 200,
            'body': json.dumps(response['Item']),
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