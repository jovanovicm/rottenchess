import json
from urllib import request, error
import boto3
import os
import re
from datetime import datetime, timedelta

def lambda_handler(event, context):
    try:
        USER_AGENT_EMAIL = get_secret()
        BUCKET_NAME = os.getenv('BUCKET_NAME')
        OBJECT_KEY_1 = os.getenv('OBJECT_KEY_1')
        OBJECT_KEY_2 = os.getenv('OBJECT_KEY_2')
        today = datetime.now().strftime("%m-%d-%Y")
        remove_period = (datetime.now() - timedelta(days=30)).strftime("%m-%d-%Y")

        # Fetch current leaderboard
        leaderboard_dict = get_leaderboard(USER_AGENT_EMAIL, today)
        tracked_dict = get_player_dict(BUCKET_NAME, OBJECT_KEY_1) or leaderboard_dict
        personality_dict = get_player_dict(BUCKET_NAME, OBJECT_KEY_2)

        # Update tracked players
        updated_tracked_dict = update_players(tracked_dict, leaderboard_dict, today, remove_period)

        # Store updated data in S3
        tracked_json = json.dumps(updated_tracked_dict, indent=2)
        upload_to_s3(BUCKET_NAME, OBJECT_KEY_1, tracked_json)

        # Collect all usernames and fetch games
        all_usernames = get_usernames(updated_tracked_dict + personality_dict)
        fetch_and_store_games(all_usernames, USER_AGENT_EMAIL)

    except Exception as e:
        print(f"Error processing: {str(e)}")
        raise e

def get_secret():
    SECRET_ARN = os.getenv('SECRET_ARN')
    AWS_REGION = os.getenv('AWS_REGION')

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=SECRET_ARN)

    secret_dict = json.loads(response['SecretString'])
    secret = secret_dict['USER_AGENT_EMAIL']

    return secret

def update_players(tracked_dict, leaderboard_dict, today, remove_period):
    updated_tracked_dict = {player['username']: player for player in leaderboard_dict}

    for player in tracked_dict:
        if player['username'] not in updated_tracked_dict:
            if player["last_seen"] >= remove_period:
                player["last_seen"] = today
                updated_tracked_dict[player['username']] = player
            else:
                print(f"Removed {player['username']} from tracked players")

    return list(updated_tracked_dict.values())

def fetch_and_store_games(usernames, USER_AGENT_EMAIL):
    for username in usernames:
        print(f"Fetching games for player: {username}")
        games = get_games(USER_AGENT_EMAIL, username, '2024', '05')
        if games:
            print(f"Storing games in DynamoDB for player: {username}")
            store_games(games)

def get_leaderboard(USER_AGENT_EMAIL, today):
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
                        "name": player["name"],
                        "rank": player["rank"],
                        "rating": player["score"],
                        "title": player["title"],
                        "country": country_code,
                        "last_seen": today
                    }

                    leaderboard_dict.append(leaderboard_player)

                return leaderboard_dict
            
    except error.URLError as e:
        print(f"Failed: {e.reason}")
        return None
        
    
def get_games(USER_AGENT_EMAIL, username, year, month):
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}"
    headers = {'User-Agent': USER_AGENT_EMAIL}
    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                games = []
                MIN_END_TIME = 1716774840
                TIME_CLASS = 'blitz'

                def extract_moves(pgn):
                    pgn = re.sub(r'\[.*?\]', '', pgn)
                    pgn = re.sub(r'\{.*?\}', '', pgn)
                    pgn = re.sub(r'\(.*?\)', '', pgn)
                    pgn = pgn.strip()
                    pgn = re.sub(r'\d+\.', '', pgn)
                    pgn = re.sub(r'\.\.', ' ', pgn)
                    pgn = re.sub(r'\s+', ' ', pgn).strip()
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

def upload_to_s3(BUCKET_NAME, OBJECT_KEY, data):
    s3 = boto3.client('s3')
    s3.put_object(Body=data, Bucket=BUCKET_NAME, Key=OBJECT_KEY)

def store_games(games):
    dynamodb = boto3.resource('dynamodb')
    TABLE_NAME = os.getenv('TABLE_NAME')
    table = dynamodb.Table(TABLE_NAME)

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


