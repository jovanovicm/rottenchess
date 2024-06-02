import boto3
import json
import os

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    GAME_IMPORTS_TABLE = os.environ('GAME_IMPORTS_TABLE')
    table = dynamodb.Table(GAME_IMPORTS_TABLE)
    
    sqs = boto3.client('sqs')
    SQS_QUEUE_URL = os.environ('SQS_QUEUE_URL')

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
            sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(items))

        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    return {'statusCode': 200, 'body': json.dumps('Items enqueued successfully')}
