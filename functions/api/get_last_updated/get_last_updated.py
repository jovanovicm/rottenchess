import boto3
import os

def lambda_handler(event, context):
    METADATA_TABLE = os.getenv('METADATA_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(METADATA_TABLE)
    
    last_updated_value = get_last_updated(table)
    
    return {
        'statusCode': 200,
        'body': last_updated_value
    }

def get_last_updated(table):
    response = table.get_item(
        Key={
            'metadata_id': 'last_updated'
        }
    )
    item = response.get('Item')
    if item:
        return item.get('timestamp')
    else:
        return 'No data available'