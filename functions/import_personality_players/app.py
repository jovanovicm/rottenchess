import json
from urllib import request
import boto3
import os

def lambda_handler(event, context):
    TRACKED_PLAYERS_TABLE = os.getenv('TRACKED_PLAYERS_TABLE')
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    USER_AGENT_EMAIL = get_secret()

    # Chess Personalities I like + me
    usernames = ['gothamchess', 'alexandrabotez', 'nemsko', 'annacramling', 'markoj000']
    
    players_info = get_players_info(usernames, USER_AGENT_EMAIL)
    store_tracked_players(players_info, TRACKED_PLAYERS_TABLE)
    update_player_stats(players_info, PLAYER_STATS_TABLE)
    
    return {
        'statusCode': 200
    }

def get_secret():
    SECRET_ARN = os.getenv('SECRET_ARN')
    AWS_REGION = os.getenv('AWS_REGION')

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=SECRET_ARN)
    secret_dict = json.loads(response['SecretString'])

    return secret_dict['USER_AGENT_EMAIL']

def get_info(username, USER_AGENT_EMAIL):
    url = f"https://api.chess.com/pub/player/{username}"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)
    
    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                country_code = data["country"].rsplit('/', 1)[-1]
                return {
                    "username": data["username"],
                    "player_name": data["name"],
                    "player_title": data.get("title", "No title"),
                    "country": country_code,
                    "is_leaderboard_player": False
                }
    except request.URLError as e:
        print(f"Error fetching data for {username}: {e.reason}")
        return None

def get_players_info(usernames, USER_AGENT_EMAIL):
    players_info = []
    for username in usernames:
        player_info = get_info(username, USER_AGENT_EMAIL)
        if player_info:
            players_info.append(player_info)
    return players_info

def store_tracked_players(players_info, TRACKED_PLAYERS_TABLE):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    
    for player in players_info:
        item = {
            "username": player["username"],
            "is_leaderboard_player": player["is_leaderboard_player"]
        }
        table.put_item(Item=item)
        print(f"Stored tracked player for {player['username']}")

def update_player_stats(players_info, PLAYER_STATS_TABLE):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PLAYER_STATS_TABLE)
    
    for player in players_info:
        table.update_item(
            Key={'username': player['username']},
            UpdateExpression="SET player_name = :pn, player_title = :pt, country = :ct",
            ExpressionAttributeValues={
                ':pn': player['player_name'],
                ':pt': player['player_title'],
                ':ct': player['country']
            }
        )
        print(f"Updated player stats for {player['username']}")

