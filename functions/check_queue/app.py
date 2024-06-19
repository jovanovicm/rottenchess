import boto3
import os

def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
    
    response = sqs.get_queue_attributes(
        QueueUrl=SQS_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    
    message_count = int(response['Attributes']['ApproximateNumberOfMessages'])

    return {
        'isEmpty': message_count == 0
    }