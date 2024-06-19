import boto3
import os

def lambda_handler(event, context):
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(GAME_IMPORTS_TABLE)

    scan_kwargs = {
        'ProjectionExpression': 'game_uuid'
    }
    done = False
    start_key = None

    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            table.delete_item(
                Key={
                    'game_uuid': item['game_uuid']
                }
            )

        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    print("All items deleted.")

    return {
        'statusCode': 200
    }
