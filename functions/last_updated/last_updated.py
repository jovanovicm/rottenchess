import boto3
from datetime import datetime, timezone, timedelta
import os

EST = timezone(timedelta(hours=-5))

def lambda_handler(event, context):
    METADATA_TABLE = os.getenv('METADATA_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(METADATA_TABLE)
    
    current_datetime = datetime.now(EST).strftime("%B %d, %Y")
    
    item = {
        'metadata_id': 'last_updated',
        'timestamp': current_datetime
    }
    
    table.put_item(Item=item)
    
    return {
        'statusCode': 200,
        'body': f"Metadata 'last_updated' set to {current_datetime}"
    }