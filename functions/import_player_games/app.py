import json
import boto3
import requests
import os

def lambda_handler(event, context):
    try:
        api_token = get_secret()
        players = get_players_list()

        for player in players:
            print(f"Fetching games for player: {player['username']}")
            games = fetch_games(api_token, player['username'], '1716422422000', 'bullet')
            if games:
                print(f"Storing games in DynamoDB for player: {player['username']}")
                store_games_in_dynamodb(games)

    except Exception as e:
        print(f"Error processing: {str(e)}")
        raise e

def get_players_list():
    s3 = boto3.client('s3')
    bucket_name = 'rotten-chess-player-info'
    response = s3.get_object(Bucket=bucket_name, Key='bullet_players_info.json')
    players = json.loads(response['Body'].read().decode('utf-8'))
    print(f"Retrieved {len(players)} players from S3.")
    return players

def get_secret():
    secret_arn = os.getenv('SECRET_ARN')
    region_name = "us-east-2"

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_arn)

    secret_dict = json.loads(get_secret_value_response['SecretString'])
    lichess_api_token = secret_dict['LICHESS_API_TOKEN']

    return lichess_api_token

def fetch_games(api_token, username, since, perfType):
    url = f'https://lichess.org/api/games/user/{username}?since={since}&perfType={perfType}'
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Accept': 'application/x-ndjson'
    }
    
    response = requests.get(url, headers=headers, stream=True)
    
    if response.status_code == 200:
        games = []
        for line in response.iter_lines():
            if line:
                game_data = json.loads(line.decode('utf-8'))
                filtered_data = {
                    "game_id": game_data["id"],
                    "perf": game_data["perf"],
                    "moves": game_data.get("moves", ""),
                    "players": {
                        "white": game_data["players"]["white"]["user"]["id"],
                        "black": game_data["players"]["black"]["user"]["id"]
                    }
                }
                games.append(filtered_data)
        store_games_in_dynamodb(games)
        print(f"Retrieved and stored {len(games)} games for {username}.")
    else:
        print(f"Failed to fetch games for {username}: HTTP {response.status_code} - {response.text}")

def store_games_in_dynamodb(games):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'rotten-chess-game-imports'
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for game in games:
            item = {
                'game_id': game['game_id'],  # Primary key
                'perf': game['perf'],
                'moves': game['moves'],
                'players': game['players']
            }
            batch.put_item(Item=item)
    print(f"Stored {len(games)} games in DynamoDB.")


