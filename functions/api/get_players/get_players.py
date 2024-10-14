import json
import boto3
import os

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
    
    response = table.scan()
    items = response['Items']

    result = {
        'leaderboard_players': {
            'active': [],
            'inactive': []
        },
        'personality_players': []
    }

    for item in items:
        if item['is_leaderboard_player']:
            if item['active']:
                result['leaderboard_players']['active'].append(item['username'])
            else:
                result['leaderboard_players']['inactive'].append(item['username'])
        else:
            result['personality_players'].append(item['username'])

    return {
        'statusCode': 200,
        'body': json.dumps(result),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': access_control_allow_origin,
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
        }
    }
