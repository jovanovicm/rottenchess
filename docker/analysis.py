import json
import chess
import chess.engine
import math
import boto3
import os
from datetime import datetime
from urllib.request import Request, urlopen


AWS_REGION = os.getenv('AWS_REGION')
QUEUE_URL = os.getenv('SQS_QUEUE_URL')
PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
ENGINE_PATH = '/usr/games/stockfish'

engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
sqs = boto3.client('sqs', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(PLAYER_STATS_TABLE)

def log_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def set_task_protection(protected):
    ECS_AGENT_URI = os.getenv('ECS_AGENT_URI')
    url = f"{ECS_AGENT_URI}/task-protection/v1/state"
    data = json.dumps({
        "protectionEnabled": protected
    }).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    req = Request(url, data=data, headers=headers, method='PUT')
    
    with urlopen(req):
        pass
    
    log_print(f"Scale-in protection set to {protected}.")

def update_player_stats(player, stats):
    response = table.get_item(Key={'username': player})
    if 'Item' not in response:
        log_print(f'Player {player} not found in the database. Skipping...')
        return
    log_print(f'Player {player} found in the database')

    current_date = datetime.now()
    year = f'y{current_date.year}'
    month = f'm{current_date.month:02}'

    keys = {'username': player}
    expression_attribute_values = {":empty_map": {}}

    initialize_paths = [
        "SET game_stats = if_not_exists(game_stats, :empty_map)",
        f"SET game_stats.{year} = if_not_exists(game_stats.{year}, :empty_map)",
        f"SET game_stats.{year}.player_total = if_not_exists(game_stats.{year}.player_total, :empty_map)",
        f"SET game_stats.{year}.{month} = if_not_exists(game_stats.{year}.{month}, :empty_map)",
        f"SET game_stats.{year}.{month}.player_total = if_not_exists(game_stats.{year}.{month}.player_total, :empty_map)"
    ]

    try:
        for expr in initialize_paths:
            table.update_item(
                Key=keys,
                UpdateExpression=expr,
                ExpressionAttributeValues=expression_attribute_values
            )
    except Exception as e:
        log_print(f"Error during initialization: {str(e)}")
        return  
    
    try:
        for stat, increment in stats.items():
            log_print(f'stat: {stat}, increment: {increment}')
            paths = [
                f"game_stats.{year}.player_total.{stat}",
                f"game_stats.{year}.{month}.player_total.{stat}"
            ]
            
            for path in paths:
                update_expression = f"SET {path} = if_not_exists({path}, :zero) + :inc_{stat}"
                expression_attribute_values = {
                    ":zero": 0,
                    f":inc_{stat}": increment
                }
                table.update_item(
                    Key=keys,
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values
                )
    except Exception as e:
        log_print(f"Error during attribute update: {str(e)}")
        return 

    log_print(f"Finished update process for player: {player}")

def decrease_task_count(cluster_name, service_name):
    ecs_client = boto3.client('ecs',
                   region_name=AWS_REGION)
    
    response = ecs_client.describe_services(
        cluster=cluster_name,
        services=[service_name]
    )

    current_desired_count = response['services'][0]['desiredCount']
    new_desired_count = max(0, current_desired_count - 1)
    
    if new_desired_count != current_desired_count:
        ecs_client.update_service(
            cluster=cluster_name,
            service=service_name,
            desiredCount=new_desired_count
        )

    log_print(f'Decreased desired count to {new_desired_count}')

def fetch_messages():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20,
        VisibilityTimeout=7200
    )
    return response.get('Messages', [])

def delete_message(receipt_handle):
    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle
    )

def analyze_moves(moves, engine, board):
    stats = {'white': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0},
             'black': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0}}
    
    def winning_chances(cp):
        MULTIPLIER = -0.004
        return 1 / (1 + math.exp(MULTIPLIER * cp))

    for i, move_san in enumerate(moves):
        player = 'white' if i % 2 == 0 else 'black'
        info_before = engine.analyse(board, chess.engine.Limit(depth=20))
        score_before = info_before['score']
        cp_before = score_before.white().score(mate_score=10000) if player == 'white' else score_before.black().score(mate_score=10000)

        try:
            move = board.parse_san(move_san)
            board.push(move)
            log_print(move_san)
        except chess.IllegalMoveError:
            log_print(f"Illegal move detected, skipping this game...")
            return None

        info_after = engine.analyse(board, chess.engine.Limit(depth=20))
        score_after = info_after['score']
        is_mate = score_after.is_mate()
        cp_after = int(score_after.white().score(mate_score=10000)) if player == 'white' else int(score_after.black().score(mate_score=10000))

        if is_mate:
            continue

        wp_before = winning_chances(cp_before)
        wp_after = winning_chances(cp_after)
        win_prob_change = abs(wp_after - wp_before)

        if win_prob_change >= 0.2:
            stats[player]['blunders'] += 1
        elif win_prob_change >= 0.1:
            stats[player]['mistakes'] += 1
        elif win_prob_change >= 0.05:
            stats[player]['inaccuracies'] += 1

    return stats

def process_message(message):
    games = json.loads(message['Body'])
    player_stats = {}
    board = chess.Board()
    for game in games:
        board.reset()
        moves = game['moves'].split()
        log_print(f"Processing game: {game['game_uuid']}")
        game_stats = analyze_moves(moves, engine, board)
        if game_stats is None:
            continue

        players = {'white': game['white'], 'black': game['black']}

        for colour, player in players.items():
            if player not in player_stats:
                player_stats[player] = {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0}
            for key in game_stats[colour]:
                player_stats[player][key] += game_stats[colour][key]
        
        log_print(f"Game processed successfully: {game['game_uuid']}")
    
    log_print(player_stats)
    
    for player, stats in player_stats.items():
        log_print(f"Updating database for player: {player} with stats: {stats}")
        update_player_stats(player, stats)

    return player_stats

def main():
    set_task_protection(True)

    messages = fetch_messages()
    for message in messages:
        process_message(message)
        delete_message(message['ReceiptHandle'])
    
    engine.quit()
    log_print('TASK COMPLETE')

    set_task_protection(False)
    decrease_task_count('rotten-chess-game-analysis', 'rotten-chess-ecs-service')

if __name__ == '__main__':
    main()

