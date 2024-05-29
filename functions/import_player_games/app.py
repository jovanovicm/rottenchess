import json
from urllib import request, error
import boto3
import os
import re

def lambda_handler(event, context):
    try:
        USER_AGENT_EMAIL = get_secret()
        BUCKET_NAME = os.getenv('BUCKET_NAME')
        OBJECT_KEY_1 = os.getenv('OBJECT_KEY_1')
        OBJECT_KEY_2 = os.getenv('OBJECT_KEY_2')

        leaderboard, leaderboard_players = get_leaderboard(USER_AGENT_EMAIL)
        upload_to_s3(BUCKET_NAME, OBJECT_KEY_1, leaderboard)

        personality_players = get_personality_players(BUCKET_NAME, OBJECT_KEY_2)

        players = list(set(leaderboard_players + personality_players))

        # Process each player
        for player in players:
            print(f"Fetching games for player: {player}")
            games = get_games(USER_AGENT_EMAIL, player, '2024', '05')
            if games:
                print(f"Storing games in DynamoDB for player: {player}")
                store_games(games)

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

def get_leaderboard(USER_AGENT_EMAIL):
    url = "https://api.chess.com/pub/leaderboards"
    headers = {'User-Agent': USER_AGENT_EMAIL}

    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                leaderboard = []
                players = []
                
                for player in data['live_blitz']:
                    country_code = player["country"].rsplit('/', 1)[-1]

                    leaderboard_player = {
                        "username": player["username"],
                        "name": player["name"],
                        "rank": player["rank"],
                        "rating": player["score"],
                        "title": player["title"],
                        "country": country_code
                    }

                    leaderboard.append(leaderboard_player)
                    players.append(player["username"])

                leaderboard_json = json.dumps(leaderboard, indent=2)

                return leaderboard_json, players
            
    except error.URLError as e:
        print(f"Failed: {e.reason}")
        return None, None
        
    
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
                    if game["end_time"] >= MIN_END_TIME and game['time_class'] == TIME_CLASS:
                        game_info = {
                            "game_uuid": game["uuid"],
                            "white": {
                                "username": game["white"]["username"],
                            },
                            "black": {
                                "username": game["black"]["username"],
                            },
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

def get_personality_players(BUCKET_NAME, OBJECT_KEY):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
    
    players_data = json.loads(response['Body'].read().decode('utf-8'))
    players = [player["username"] for player in players_data]
    
    print(f"Retrieved {len(players)} players from S3.")
    return players

def upload_to_s3(BUCKET_NAME, OBJECT_KEY, data):
    s3 = boto3.client('s3')
    try:
        s3.put_object(Body=data, Bucket=BUCKET_NAME, Key=OBJECT_KEY)
        print("File uploaded successfully to S3.")
    except Exception as e:
        print(f"Failed to upload file to S3: {e}")

def store_games(games):
    dynamodb = boto3.resource('dynamodb')
    TABLE_NAME = os.getenv('TABLE_NAME')
    table = dynamodb.Table(TABLE_NAME)

    with table.batch_writer() as batch:
        for game in games:
            item = {
                "game_uuid": game["game_uuid"], # Primary Key
                "white": {
                    "username": game["white"]["username"],
                },
                "black": {
                    "username": game["black"]["username"],
                },
                "game_url": game["game_url"],
                "end_time": game["end_time"],
                "time_class": game["time_class"],
                "moves": game["moves"]
            }

            batch.put_item(Item=item)
    print(f"Stored {len(games)} games in DynamoDB.")


