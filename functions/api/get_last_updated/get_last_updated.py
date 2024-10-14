import boto3
import os

def lambda_handler(event, context):
    METADATA_TABLE = os.getenv('METADATA_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(METADATA_TABLE)

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
    
    last_updated_value = get_last_updated(table)
    
    return {
        'statusCode': 200,
        'body': last_updated_value,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': access_control_allow_origin,
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date'
        }
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