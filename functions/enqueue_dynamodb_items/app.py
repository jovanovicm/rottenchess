import boto3
import json
import os

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['PLAYER_GAMES_TABLE_NAME'])
    sqs = boto3.client('sqs')
    queue_url = os.environ['SQS_QUEUE_URL']

    # Initialize scan parameters
    scan_kwargs = {
        'Limit': 5
    }
    done = False
    start_key = None

    # Scan DynamoDB and enqueue messages
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        # Send batch to SQS
        if items:
            sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(items))

        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    return {'statusCode': 200, 'body': json.dumps('Items enqueued successfully')}
