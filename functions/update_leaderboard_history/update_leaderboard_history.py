import boto3
from datetime import datetime
import os

PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
LEADERBOARD_HISTORY_TABLE = os.getenv('LEADERBOARD_HISTORY_TABLE')

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    stats_table = dynamodb.Table(PLAYER_STATS_TABLE)
    leaderboard_table = dynamodb.Table(LEADERBOARD_HISTORY_TABLE)

    date = datetime.now().strftime('%Y/%m')
    
    # Scan PlayerStats table to get all active players
    response_leaderboard = stats_table.scan(
        FilterExpression="attribute_exists(active) AND active = :a",
        ExpressionAttributeValues={":a": True}
    )
    leaderboard_players = response_leaderboard['Items']
    
    # Scan PlayerStats table to get all personality players
    response_personality = stats_table.scan(
        FilterExpression="attribute_exists(is_leaderboard_player) AND is_leaderboard_player = :l",
        ExpressionAttributeValues={":l": False}
    )
    personality_players = response_personality['Items']

    player_stats = {}
    for player in leaderboard_players:
        player_stats[player['username']] = {
            'player_rank': player['player_rank'],
            'rating': player['rating'],

        }
    for player in personality_players:
        player_stats[player['username']] = {
            'rating': player['rating']
        }
    
    leaderboard_table.put_item(
        Item={
            'date': date,
            'players': player_stats
        }
    )

    return {
        'statusCode': 200,
    }