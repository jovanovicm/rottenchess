import boto3
import os

def lambda_handler(event, context):
    PROCESSED_GAMES_TABLE = os.getenv('PROCESSED_GAMES_TABLE')
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    dynamodb = boto3.resource('dynamodb')

    game_imports_table = dynamodb.Table(GAME_IMPORTS_TABLE)
    processed_games_table = dynamodb.Table(PROCESSED_GAMES_TABLE)

    delete_items_from_table(game_imports_table, 'game_uuid')
    delete_items_from_table(processed_games_table, 'message_id')

    return {
        'statusCode': 200,
        'body': 'All items deleted from both tables.'
    }

def delete_items_from_table(table, primary_key):
    scan_kwargs = {
        'ProjectionExpression': primary_key
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
                    primary_key: item[primary_key]
                }
            )

        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    print(f"All items deleted from table {table.name}.")
