import boto3
import os

def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
    
    response = sqs.get_queue_attributes(
        QueueUrl=SQS_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    
    visible_message_count = int(response['Attributes']['ApproximateNumberOfMessages'])
    in_flight_message_count = int(response['Attributes']['ApproximateNumberOfMessagesNotVisible'])

    print(f"inflight: {in_flight_message_count}")
    print(f"visible: {visible_message_count}")

    return {
        'isEmpty': visible_message_count == 0 and in_flight_message_count == 0
    }