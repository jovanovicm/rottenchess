import json
from urllib import request, error
import boto3
import os
import re
from datetime import datetime, timedelta

def lambda_handler(event, context):
    USER_AGENT_EMAIL = get_secret()
    TRACKED_PLAYERS_TABLE = os.getenv('TRACKED_PLAYERS_TABLE')
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    today = datetime.now().strftime("%m-%d-%Y")
    remove_period = (datetime.now() - timedelta(days=30)).strftime("%m-%d-%Y")

    # Fetch current leaderboard
    leaderboard_dict = get_leaderboard(USER_AGENT_EMAIL)

    # Update tracked players and stats
    update_player_dbs(TRACKED_PLAYERS_TABLE, PLAYER_STATS_TABLE, leaderboard_dict, today, remove_period)

    dynamodb = boto3.resource('dynamodb')
    tracked_dict = get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb)

    # Collect all usernames and fetch games
    all_usernames = [player['username'] for player in tracked_dict]
    fetch_and_store_games(USER_AGENT_EMAIL, GAME_IMPORTS_TABLE, all_usernames)

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
    secret = secret_dict['USER_AGENT_EMAIL']

    return secret

def update_player_dbs(TRACKED_PLAYERS_TABLE, PLAYER_STATS_TABLE, leaderboard_dict, today, remove_period):
    dynamodb = boto3.resource('dynamodb')
    tracked_table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    stats_table = dynamodb.Table(PLAYER_STATS_TABLE)

    tracked_dict = get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb)

    # Update TrackedPlayers Table
    for player in leaderboard_dict:
        tracked_table.update_item(
            Key={'username': player['username']},
            UpdateExpression="SET last_seen = :ls, is_leaderboard_player = :ilp",
            ExpressionAttributeValues={
                ':ls': today,
                ':ilp': True
            }
        )

        # Update PlayerStats Table
        stats_table.update_item(
            Key={'username': player['username']},
            UpdateExpression="SET player_name = :pn, player_rank = :pr, rating = :rt, player_title = :pt, country = :c",
            ExpressionAttributeValues={
                ':pn': player['player_name'],
                ':pr': player['player_rank'],
                ':rt': player['rating'],
                ':pt': player['player_title'],
                ':c': player['country'],
            }
        )

    # Leaderboard Inactivty Check
    for player in tracked_dict:
        if player.get('last_seen', '01-01-2000') <= remove_period and player['is_leaderboard_player'] == True:
            tracked_table.delete_item(Key={'username': player['username']})

            print(f"Removed {player['username']} from tracked players due to inactivity in leaderboard")


def fetch_and_store_games(USER_AGENT_EMAIL, GAME_IMPORTS_TABLE, usernames):
    for username in usernames:
        print(f"Fetching games for player: {username}")
        games = get_games(USER_AGENT_EMAIL, 1717027200, 'blitz', username, '2024', '05')
        if games:
            print(f"Storing games in DynamoDB for player: {username}")
            store_game_imports(GAME_IMPORTS_TABLE, games)

def get_leaderboard(USER_AGENT_EMAIL):
    url = "https://api.chess.com/pub/leaderboards"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                leaderboard_dict = []
                
                for player in data['live_blitz']:
                    country_code = player["country"].rsplit('/', 1)[-1]

                    leaderboard_player = {
                        "username": player["username"],
                        "player_name": player["name"],
                        "player_rank": player["rank"],
                        "rating": player["score"],
                        "player_title": player["title"],
                        "country": country_code,
                        "last_seen": None,
                        "is_leaderboard_player": None
                    }

                    leaderboard_dict.append(leaderboard_player)

                return leaderboard_dict
            
    except error.URLError as e:
        print(f"Failed: {e.reason}")
        return None
    
def get_games(USER_AGENT_EMAIL, MIN_END_TIME, TIME_CLASS, username, year, month):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    headers = {'User-Agent': USER_AGENT_EMAIL}
    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                games = []
                MIN_END_TIME = 1717200000
                TIME_CLASS = 'blitz'

                def extract_moves(pgn):
                    pgn = re.sub(r'\[.*?\]', '', pgn)
                    pgn = re.sub(r'\{.*?\}', '', pgn)
                    pgn = re.sub(r'\(.*?\)', '', pgn)
                    pgn = pgn.strip()
                    pgn = re.sub(r'\d+\.', '', pgn)
                    pgn = re.sub(r'\.\.', ' ', pgn)
                    pgn = re.sub(r'\s+', ' ', pgn).strip()
                    pgn = re.sub(r'1/2\-1/2|1\-0|0\-1$', '', pgn).strip()
                    return pgn

                for game in data["games"]:
                    # Ensure all required fields are present
                    if all(key in game for key in ['end_time', 'time_class', 'pgn']) and \
                       game['end_time'] >= MIN_END_TIME and \
                       game['time_class'] == TIME_CLASS:
                        game_info = {
                            "game_uuid": game["uuid"],
                            "white": game["white"],
                            "black": game["black"],
                            "game_url": game["url"],
                            "end_time": game["end_time"],
                            "time_class": game["time_class"],
                            "moves": extract_moves(game["pgn"])
                        }
                        games.append(game_info)

                return games
            
    except error.URLError as e:
        print(f"Failed: {e.reason}")
        return None
    except KeyError as e:
        print(f"Missing expected game data key: {e} - Continuing with other games")
        return None

def get_player_dict(BUCKET_NAME, OBJECT_KEY):
    try:
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)

        return json.loads(response['Body'].read().decode('utf-8'))
    
    except json.JSONDecodeError:
        return []

def get_usernames(player_data):
    return [player["username"] for player in player_data]

def get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb):
    table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    response = table.scan()

    return response['Items']


def store_game_imports(GAME_IMPORTS_TABLE, games):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(GAME_IMPORTS_TABLE)

    with table.batch_writer() as batch:
        for game in games:
            item = {
                "game_uuid": game["game_uuid"], # Primary Key
                "white": game["white"]["username"],
                "black": game["black"]["username"],
                "game_url": game["game_url"],
                "end_time": game["end_time"],
                "time_class": game["time_class"],
                "moves": game["moves"]
            }

            batch.put_item(Item=item)
    print(f"Stored {len(games)} games in DynamoDB.")


