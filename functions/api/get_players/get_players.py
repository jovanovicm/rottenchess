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

    # Extract query parameters
    query_params = event.get('queryStringParameters') or {}

    list_param = query_params.get('list')
    usernames_param = query_params.get('usernames')

    if list_param:
        # Handle listing all players
        items = []
        last_evaluated_key = None

        while True:
            if last_evaluated_key:
                response = table.scan(ExclusiveStartKey=last_evaluated_key)
            else:
                response = table.scan()
            items.extend(response.get('Items', []))
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        result = {
            'leaderboard_players': {
                'active': [],
                'inactive': []
            },
            'personality_players': []
        }

        for item in items:
            if item.get('is_leaderboard_player'):
                if item.get('active'):
                    result['leaderboard_players']['active'].append(item['username'])
                else:
                    result['leaderboard_players']['inactive'].append(item['username'])
            else:
                result['personality_players'].append(item['username'])

        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': headers
        }

    elif usernames_param:
        # Handle retrieving stats for specific usernames
        usernames = [u.strip() for u in usernames_param.split(',') if u.strip()]
        if not usernames:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No valid usernames provided'}),
                'headers': headers
            }

        all_items = []
        for i in range(0, len(usernames), 100):
            batch_usernames = usernames[i:i+100]
            keys = [{'username': username} for username in batch_usernames]
            response = dynamodb.batch_get_item(
                RequestItems={
                    PLAYER_STATS_TABLE: {
                        'Keys': keys
                    }
                }
            )
            items = response.get('Responses', {}).get(PLAYER_STATS_TABLE, [])
            converted_items = [convert_decimals(item) for item in items]
            all_items.extend(converted_items)

            # Handle unprocessed keys
            while response.get('UnprocessedKeys'):
                response = dynamodb.batch_get_item(
                    RequestItems=response['UnprocessedKeys']
                )
                items = response.get('Responses', {}).get(PLAYER_STATS_TABLE, [])
                converted_items = [convert_decimals(item) for item in items]
                all_items.extend(converted_items)

        return {
            'statusCode': 200,
            'body': json.dumps(all_items),
            'headers': headers
        }

    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request. Specify either ?list=true or ?usernames=user1,user2'}),
            'headers': headers
        }