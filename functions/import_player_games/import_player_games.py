import json
from urllib import request, error
import boto3
import os
import re
from datetime import datetime, timedelta, timezone
import time

def lambda_handler(event, context):
    USER_AGENT_EMAIL = get_secret()
    TRACKED_PLAYERS_TABLE = os.getenv('TRACKED_PLAYERS_TABLE')
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    today = datetime.now().strftime("%m-%d-%Y")
    remove_period = (datetime.now() - timedelta(days=30)).strftime("%m-%d-%Y")

    # Chess Personalities + me
    chess_personalities = [
        'markoj000',
        'gothamchess',
        'alexandrabotez',
        'supersecret12345',
        'nemsko', 
        'annacramling',
    ]

    leaderboard_dict = get_leaderboard(USER_AGENT_EMAIL)
    chess_personalities_info = get_players_info(chess_personalities, USER_AGENT_EMAIL)

    update_player_dbs(TRACKED_PLAYERS_TABLE, PLAYER_STATS_TABLE, leaderboard_dict, chess_personalities_info, today, remove_period)

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

def update_player_dbs(TRACKED_PLAYERS_TABLE, PLAYER_STATS_TABLE, leaderboard_players, chess_personalities, today, remove_period):
    dynamodb = boto3.resource('dynamodb')
    tracked_table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    stats_table = dynamodb.Table(PLAYER_STATS_TABLE)

    tracked_dict = get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb)

    current_leaderboard_usernames = set()

    # Update TrackedPlayers Table and PlayerStats Table for leaderboard players
    for player in leaderboard_players:
        username = player['username']
        current_leaderboard_usernames.add(username)
        
        # Update TrackedPlayers
        tracked_table.put_item(
            Item={
                'username': username,
                'last_seen': today,
                'is_leaderboard_player': True
            }
        )

        # Update PlayerStats
        stats_table.put_item(
            Item={
                'username': username,
                'player_name': player['player_name'],
                'player_rank': player['player_rank'],
                'rating': player['rating'],
                'player_title': player['player_title'],
                'country': player['country'],
                'is_leaderboard_player': True,
                'active': True
            }
        )

    # Update TrackedPlayers Table and PlayerStats Table for chess personalities
    for player in chess_personalities:
        username = player['username']
        
        # Update TrackedPlayers
        tracked_table.put_item(
            Item={
                'username': username,
                'is_leaderboard_player': False
            }
        )

        # Update PlayerStats
        stats_table.put_item(
            Item={
                'username': username,
                'player_name': player['player_name'],
                'rating': player['rating'],
                'player_title': player['player_title'],
                'country': player['country'],
                'is_leaderboard_player': False
            }
        )

    # Check for players no longer on the leaderboard
    for player in tracked_dict:
        username = player['username']
        if player['is_leaderboard_player'] and username not in current_leaderboard_usernames:
            # Player left the leaderboard
            stats_table.update_item(
                Key={'username': username},
                UpdateExpression="SET active = :a",
                ExpressionAttributeValues={
                    ':a': False,
                }
            )
            print(f"Marked {username} as inactive in PlayerStats table due to leaving the leaderboard")

            # Remove tracking after being inactive for 30 days
            if player['last_seen'] <= remove_period:
                tracked_table.delete_item(Key={'username': username})
                print(f"Deleted {username} from TrackedPlayers table due to inactivity")

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
                        "username": player["username"].lower(),
                        "player_name": player.get("name", "Unknown Player"),
                        "player_rank": player["rank"],
                        "rating": player["score"],
                        "player_title": player.get("title", "None"),
                        "country": country_code,
                    }

                    leaderboard_dict.append(leaderboard_player)

                return leaderboard_dict
            
    except error.URLError as e:
        print(f"Failed: {e.reason}")
        return None

def get_players_info(usernames, USER_AGENT_EMAIL):
    players_info = []
    for username in usernames:
        player_info = get_player_stats(username, USER_AGENT_EMAIL)
        if player_info:
            players_info.append(player_info)
    return players_info

def get_player_stats(username, USER_AGENT_EMAIL):
    url = f"https://api.chess.com/pub/player/{username}/stats"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)
    
    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                player_info = get_info(username, USER_AGENT_EMAIL)
                if player_info:
                    player_info['rating'] = data['chess_blitz']['last']['rating']
                    # Only set player_rank for leaderboard players
                    if player_info['is_leaderboard_player'] == False:
                        player_info['player_rank'] = data['chess_blitz']['last']['rank']
                    return player_info
    except request.URLError as e:
        print(f"Error fetching stats for {username}: {e.reason}")
        return None

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
                    "username": data["username"].lower(),
                    "player_name": data.get("name", "Unknown Player"),
                    "player_title": data.get("title", "None"),
                    "country": country_code,
                }
    except request.URLError as e:
        print(f"Error fetching data for {username}: {e.reason}")
        return None

def get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb):
    table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    response = table.scan()

    return response['Items']

def fetch_and_store_games(USER_AGENT_EMAIL, GAME_IMPORTS_TABLE, usernames):
    now_datetime = datetime.now(timezone.utc)
    target_datetime = now_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    epoch_time = int(time.mktime(target_datetime.timetuple()))

    print(f"Fetching games from: {target_datetime.strftime('%Y-%m-%d')} (epoch: {epoch_time})")

    for username in usernames:
        print(f"Fetching games for player: {username}")
        games = get_games(USER_AGENT_EMAIL, epoch_time, 'blitz', username, target_datetime.strftime('%Y'), target_datetime.strftime('%m'))
        if games:
            print(f"Storing games in DynamoDB for player: {username}")
            store_game_imports(GAME_IMPORTS_TABLE, games)

def get_games(USER_AGENT_EMAIL, MIN_END_TIME, TIME_CLASS, username, year, month):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    headers = {'User-Agent': USER_AGENT_EMAIL}
    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                games = []

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

def store_game_imports(GAME_IMPORTS_TABLE, games):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(GAME_IMPORTS_TABLE)

    with table.batch_writer() as batch:
        for game in games:
            item = {
                "game_uuid": game["game_uuid"],  # Primary Key
                "white": game["white"]["username"].lower(),
                "black": game["black"]["username"].lower(),
                "game_url": game["game_url"],
                "end_time": game["end_time"],
                "time_class": game["time_class"],
                "moves": game["moves"],
            }
            batch.put_item(Item=item)
    print(f"Stored {len(games)} games in DynamoDB.")

