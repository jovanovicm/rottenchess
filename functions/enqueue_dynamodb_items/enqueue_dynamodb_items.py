import json
import boto3
import os
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def calculate_total_time(total_games, games_per_message):
    if games_per_message == 0:
        return None  # Return None for invalid input
    
    num_messages = (total_games + games_per_message - 1) // games_per_message
    time_for_first_message = games_per_message * 5
    total_time = time_for_first_message + (num_messages - 1)
    return total_time

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    table = dynamodb.Table(GAME_IMPORTS_TABLE)
    
    sqs = boto3.client('sqs')
    SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')

    total_games = 0
    scan_kwargs = {'Select': 'COUNT'}
    start_key = None
    while True:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        total_games += response['Count']
        start_key = response.get('LastEvaluatedKey', None)
        if not start_key:
            break

    min_time = float('inf')
    optimal_games_per_message = 0
    for games_per_message in range(1, 51):
        total_time = calculate_total_time(total_games, games_per_message)
        if total_time is not None and total_time < min_time:
            min_time = total_time
            optimal_games_per_message = games_per_message
    
    print(f"Total number of games: {total_games}")
    print(f"Optimal number of games per message: {optimal_games_per_message} with a total time of {min_time} minutes")

    scan_kwargs = {'Limit': optimal_games_per_message}
    start_key = None
    while True:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        if items:
            sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(items, cls=DecimalEncoder))
        start_key = response.get('LastEvaluatedKey', None)
        if not start_key:
            break

    return {
        'statusCode': 200,
        'body': 'Completed processing'
    }
