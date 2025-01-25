import json
from urllib import request, error
import boto3
import os
import re
from datetime import datetime, timedelta, timezone
import time

def lambda_handler(event, context):
    USER_AGENT_EMAIL = get_parameter()
    TRACKED_PLAYERS_TABLE = os.getenv('TRACKED_PLAYERS_TABLE')
    PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
    GAME_IMPORTS_TABLE = os.getenv('GAME_IMPORTS_TABLE')
    today = datetime.now().strftime("%m-%d-%Y")
    remove_period = (datetime.now() - timedelta(days=30)).strftime("%m-%d-%Y")

    # Chess Personalities + me and my bro
    chess_personalities = [
        {'username': 'markoj000', 'display': 'username'}, # dev 1
        {'username': 'uberdestroyer', 'display': 'username'}, # my drunk chess account
        {'username': 'brydog123', 'display': 'username'}, # dev 2
        {'username': 'gothamchess', 'display': 'name'},
        {'username': 'alexandrabotez', 'display': 'name'},
        {'username': 'supersecret12345', 'display': 'username'},
        {'username': 'nemsko', 'display': 'name'}, 
        {'username': 'annacramling', 'display': 'name'},
        {'username': 'chessbrah', 'display': 'name'},
        {'username': 'imrosen', 'display': 'name'},
        {'username': 'Chess_Knowledge_With_H1', 'display': 'username'},
        {'username': 'thechessnerd', 'display': 'username'},
        {'username': 'GMBenjaminFinegold', 'display': 'name'},
        {'username': 'HannahSayce', 'display': 'name'},
        {'username': 'Blitzstream', 'display': 'username'},
        {'username': 'janistantv', 'display': 'username'},
        {'username': 'roseychess', 'display': 'name'},
        {'username': 'gmcanty', 'display': 'username'},
        {'username': 'metharina', 'display': 'username'},
        {'username': 'joebruin', 'display': 'username'},
        {'username': 'annamaja', 'display': 'username'}
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

def get_parameter():
    PARAMETER_NAME = os.getenv('PARAMETER_NAME')
    AWS_REGION = os.getenv('AWS_REGION') 

    session = boto3.session.Session()
    client = session.client(service_name='ssm', region_name=AWS_REGION)

    response = client.get_parameter(
        Name=PARAMETER_NAME,
        WithDecryption=False
    )

    parameter_value = response['Parameter']['Value']
    return parameter_value

def update_player_dbs(TRACKED_PLAYERS_TABLE, PLAYER_STATS_TABLE, leaderboard_players, chess_personalities, today, remove_period):
    dynamodb = boto3.resource('dynamodb')
    tracked_table = dynamodb.Table(TRACKED_PLAYERS_TABLE)
    stats_table = dynamodb.Table(PLAYER_STATS_TABLE)

    tracked_dict = get_tracked_dict(TRACKED_PLAYERS_TABLE, dynamodb)

    current_leaderboard_usernames = set()

    for player in leaderboard_players:
        username = player['username']
        current_leaderboard_usernames.add(username)
        
        # Update TrackedPlayers
        tracked_table.update_item(
            Key={'username': username},
            UpdateExpression="SET last_seen = :ls, is_leaderboard_player = :ilp",
            ExpressionAttributeValues={
                ':ls': today,
                ':ilp': True
            }
        )

        # Update PlayerStats
        stats_table.update_item(
            Key={'username': username},
            UpdateExpression="SET player_name = :pn, player_rank = :pr, rating = :r, player_title = :pt, country = :c, is_leaderboard_player = :ilp, active = :a",
            ExpressionAttributeValues={
                ':pn': player['player_name'],
                ':pr': player['player_rank'],
                ':r': player['rating'],
                ':pt': player['player_title'],
                ':c': player['country'],
                ':ilp': True,
                ':a': True
            }
        )

    for player in chess_personalities:
        username = player['username']
        
        # Update TrackedPlayers
        tracked_table.update_item(
            Key={'username': username},
            UpdateExpression="SET is_leaderboard_player = :ilp",
            ExpressionAttributeValues={
                ':ilp': False
            }
        )

        # Update PlayerStats
        stats_table.update_item(
            Key={'username': username},
            UpdateExpression="SET player_name = :pn, rating = :r, player_title = :pt, country = :c, is_leaderboard_player = :ilp",
            ExpressionAttributeValues={
                ':pn': player['player_name'],
                ':r': player['rating'],
                ':pt': player['player_title'],
                ':c': player['country'],
                ':ilp': False
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
                        "player_name": player.get("name", player["username"].lower()),
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

def get_players_info(personalities, USER_AGENT_EMAIL):
    players_info = []
    for personality in personalities:
        player_info = get_player_stats(personality['username'], USER_AGENT_EMAIL, personality['display'])
        if player_info:
            players_info.append(player_info)
    return players_info

def get_player_stats(username, USER_AGENT_EMAIL, display_preference):
    url = f"https://api.chess.com/pub/player/{username}/stats"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)
    
    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                player_info = get_info(username, USER_AGENT_EMAIL, display_preference)
                if player_info:
                    player_info['rating'] = data['chess_blitz']['last']['rating']
                    return player_info
    except request.URLError as e:
        print(f"Error fetching stats for {username}: {e.reason}")
        return None

def get_info(username, USER_AGENT_EMAIL, display_preference):
    url = f"https://api.chess.com/pub/player/{username}"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)
    
    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                country_code = data["country"].rsplit('/', 1)[-1]
                display_name = data.get("name", data["username"].lower()) if display_preference == 'name' else data["username"].lower()
                return {
                    "username": data["username"].lower(),
                    "player_name": display_name,
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
    start_datetime = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=0, minute=0, second=0)
    start_epoch_time = int(time.mktime(start_datetime.timetuple()))

    end_datetime = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=23, minute=59, second=59)
    end_epoch_time = int(time.mktime(end_datetime.timetuple()))

    print(f"Fetching games: Start ({start_datetime.strftime('%Y-%m-%d %H:%M:%S')} epoch: {start_epoch_time}) to End ({end_datetime.strftime('%Y-%m-%d %H:%M:%S')} epoch: {end_epoch_time})")

    for username in usernames:
        print(f"Fetching games for player: {username}")
        games = get_games(USER_AGENT_EMAIL, start_epoch_time, end_epoch_time, 'blitz', username, start_datetime.strftime('%Y'), start_datetime.strftime('%m'))
        if games:
            print(f"Storing games in DynamoDB for player: {username}")
            store_game_imports(GAME_IMPORTS_TABLE, games)

def get_games(USER_AGENT_EMAIL, MIN_END_TIME, MAX_END_TIME, TIME_CLASS, username, year, month):
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
                       MAX_END_TIME >= game['end_time'] >= MIN_END_TIME and \
                       game['time_class'] == TIME_CLASS and \
                       game['rules'] == 'chess':
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

