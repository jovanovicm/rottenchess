import json
import boto3
import os

def lambda_handler(event, context):
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PLAYER_STATS_TABLE)
    
    response = table.scan()
    items = response['Items']

    usernames = [item['username'] for item in items]
    
    return {
        'statusCode': 200,
        'body': json.dumps(usernames),
        'headers': {
            'Content-Type': 'application/json'
        }
    }