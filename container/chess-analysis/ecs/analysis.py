import json
import chess
import chess.engine
import math
import boto3
import os
from datetime import timezone, datetime
from urllib.request import Request, urlopen
import signal

AWS_REGION = os.getenv('AWS_REGION')
QUEUE_URL = os.getenv('SQS_QUEUE_URL')
PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
ECS_SERVICE_NAME = os.getenv('ECS_SERVICE_NAME')
ECS_CLUSTER_NAME = os.getenv('ECS_CLUSTER_NAME')
PROCESSED_GAMES_TABLE = os.getenv('PROCESSED_GAMES_TABLE')
ECS_AGENT_URI = os.getenv('ECS_AGENT_URI')

shutdown_flag = False
message = None

def init_resources():
    global sqs, table, processed_games_table, player_stats_table
    sqs = boto3.client('sqs', region_name=AWS_REGION)
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    player_stats_table = dynamodb.Table(PLAYER_STATS_TABLE)
    processed_games_table = dynamodb.Table(PROCESSED_GAMES_TABLE)

def log_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def init_engine(path='/usr/games/stockfish'):
    global engine
    engine = chess.engine.SimpleEngine.popen_uci(path)

def shutdown():
    set_task_protection(False)
    decrease_task_count(ECS_CLUSTER_NAME, ECS_SERVICE_NAME)

def signal_handler(signum, frame):
    global shutdown_flag, message

    try:
        if message and len(message) > 0:
            sqs.change_message_visibility(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message[0]['ReceiptHandle'],
                VisibilityTimeout=0
            )
    except IndexError:
        log_print("Error: message list is empty during shutdown.")
    except Exception as e:
        log_print(f"Error during message visibility change: {str(e)}")
    
    shutdown()
    shutdown_flag = True
    log_print("Shutdown signal received. Shutting down...")

def mark_game_as_processed(message_id, game_uuid, processed_games_table):
    processed_games_table.update_item(
        Key={'message_id': message_id},
        UpdateExpression="SET game_ids = list_append(if_not_exists(game_ids, :empty_list), :game_uuid)",
        ExpressionAttributeValues={
            ':empty_list': [],
            ':game_uuid': [game_uuid]
        }
    )

def get_processed_games(message_id, processed_games_table):
    log_print(f'Getting list of processed games for message ID: {message_id}')
    response = processed_games_table.get_item(
        Key={'message_id': message_id}
    )
    processed_games = response.get('Item', {}).get('game_ids', [])
    log_print(f'Processed games: {processed_games}')
    return processed_games

def set_task_protection(protected):
    url = f"{ECS_AGENT_URI}/task-protection/v1/state"
    data = json.dumps({
        "protectionEnabled": protected
    }).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    req = Request(url, data=data, headers=headers, method='PUT')
    
    with urlopen(req):
        pass
    
    log_print(f"Scale-in protection set to {protected}.")

def update_player_stats(player, stats, year, month, game_info, player_stats_table, total_games_increment):
    keys = {'username': player}

    # Initialize paths
    initialize_map_paths = [
        "SET game_stats = if_not_exists(game_stats, :empty_map)",
        f"SET game_stats.{year} = if_not_exists(game_stats.{year}, :empty_map)",
        f"SET game_stats.{year}.player_total = if_not_exists(game_stats.{year}.player_total, :empty_map)",
        f"SET game_stats.{year}.worst_game = if_not_exists(game_stats.{year}.worst_game, :empty_map)",
        f"SET game_stats.{year}.{month} = if_not_exists(game_stats.{year}.{month}, :empty_map)",
        f"SET game_stats.{year}.{month}.player_total = if_not_exists(game_stats.{year}.{month}.player_total, :empty_map)",
        f"SET game_stats.{year}.{month}.worst_game = if_not_exists(game_stats.{year}.{month}.worst_game, :empty_map)"
    ]

    initialize_zero_paths = [
        f"SET game_stats.{year}.total_games = if_not_exists(game_stats.{year}.total_games, :zero)",
        f"SET game_stats.{year}.{month}.total_games = if_not_exists(game_stats.{year}.{month}.total_games, :zero)"
    ]

    # Apply map initializations
    for expr in initialize_map_paths:
        player_stats_table.update_item(
            Key=keys,
            UpdateExpression=expr,
            ExpressionAttributeValues={":empty_map": {}}
        )

    # Apply zero initializations
    for expr in initialize_zero_paths:
        player_stats_table.update_item(
            Key=keys,
            UpdateExpression=expr,
            ExpressionAttributeValues={":zero": 0}
        )

    # Update the total_games
    update_expression = f"ADD game_stats.{year}.total_games :inc_games, game_stats.{year}.{month}.total_games :inc_games"
    player_stats_table.update_item(
        Key=keys,
        UpdateExpression=update_expression,
        ExpressionAttributeValues={":inc_games": total_games_increment}
    )

    # Update the statistical attributes and worst game
    for stat, increment in stats.items():
        yearly_path = f"game_stats.{year}.player_total.{stat}"
        monthly_path = f"game_stats.{year}.{month}.player_total.{stat}"
        
        update_expression = f"ADD {yearly_path} :inc, {monthly_path} :inc"
        player_stats_table.update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues={":inc": increment}
        )

    # Fetch current item to compare worst games
    response = player_stats_table.get_item(Key=keys)
    item = response.get('Item', {})
    game_stats = item.get('game_stats', {})
    year_stats = game_stats.get(year, {})
    month_stats = year_stats.get(month, {})

    yearly_worst_game = year_stats.get('worst_game', {'magnitude': -1})
    monthly_worst_game = month_stats.get('worst_game', {'magnitude': -1})

    # Update worst game for year
    if game_info['magnitude'] > yearly_worst_game.get('magnitude', -1):
        update_expression = f"SET game_stats.{year}.worst_game = :game_info"
        player_stats_table.update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues={":game_info": game_info}
        )
        log_print(f"Updated yearly worst game for {player} in {year}: {game_info}")

    # Update worst game for month
    if game_info['magnitude'] > monthly_worst_game.get('magnitude', -1):
        update_expression = f"SET game_stats.{year}.{month}.worst_game = :game_info"
        player_stats_table.update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues={":game_info": game_info}
        )
        log_print(f"Updated monthly worst game for {player} in {month}/{year}: {game_info}")

    log_print(f"Updated stats for {player} in {month}/{year}: {stats}")

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

def fetch_message():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=20,
        VisibilityTimeout=7200
    )
    global message
    message = response.get('Messages', [])

def delete_message(receipt_handle, sqs):
    if message:    
        sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=receipt_handle
        )

def analyze_moves(moves, engine, board):
    stats = {'white': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0},
             'black': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0}}

    def winning_chances(cp):
        MULTIPLIER = -0.00368208
        return 1 / (1 + math.exp(MULTIPLIER * cp))

    for i, move_san in enumerate(moves):
        player = 'white' if i % 2 == 0 else 'black'
        try:
            # Analyze before the move
            info_before = engine.analyse(board, chess.engine.Limit(depth=20))
            score_before = info_before['score']
            cp_before = score_before.white().score(mate_score=10000) if player == 'white' else score_before.black().score(mate_score=10000)

            # Parse and apply the move
            move = board.parse_san(move_san)
            board.push(move)
            log_print(move_san)

            # Analyze after the move
            info_after = engine.analyse(board, chess.engine.Limit(depth=20))
            score_after = info_after['score']
            cp_after = int(score_after.white().score(mate_score=10000)) if player == 'white' else int(score_after.black().score(mate_score=10000))

            wp_before = winning_chances(cp_before)
            wp_after = winning_chances(cp_after)
            win_prob_change = abs(wp_after - wp_before)

            if win_prob_change >= 0.2:
                stats[player]['blunders'] += 1
            elif win_prob_change >= 0.1:
                stats[player]['mistakes'] += 1
            elif win_prob_change >= 0.05:
                stats[player]['inaccuracies'] += 1

        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
            log_print(f"Move error detected: {str(e)}, invalid move: {move_san}")
            raise

    return stats

def process_message(message, engine, player_stats_table, processed_games_table, sqs):
    message_id = message[0]['MessageId']
    games = json.loads(message[0]['Body'])
    board = chess.Board()
    processed_games = get_processed_games(message_id, processed_games_table)

    for game in games:
        if game['game_uuid'] in processed_games:
            log_print(f'Skipping already processed game: {game["game_uuid"]}')
            continue

        board.reset()
        moves = game['moves'].split()
        end_time = datetime.fromtimestamp(game['end_time'], timezone.utc)
        year = f'y{end_time.year}'
        month = f'm{end_time.month:02}'
        
        log_print(f"Processing game: {game['game_uuid']}")
        
        try:
            game_stats = analyze_moves(moves, engine, board)
        except Exception as e:
            log_print(f"Error analyzing game {game['game_uuid']}: {str(e)}")
            continue

        players = {'white': game['white'], 'black': game['black']}

        for colour, player in players.items():
            response = player_stats_table.get_item(Key={'username': player})
            if 'Item' not in response:
                log_print(f'Player {player} not found in the database. Skipping...')
                continue

            current_stats = game_stats[colour]
            
            # Calculate magnitude for the game
            game_magnitude = current_stats['blunders'] * 3 + current_stats['mistakes'] * 2 + current_stats['inaccuracies']
            
            game_info = {
                'game_url': game['game_url'],
                'magnitude': game_magnitude,
                'stats': current_stats
            }
            
            update_player_stats(player, current_stats, year, month, game_info, player_stats_table, 1)
        
        mark_game_as_processed(message_id, game['game_uuid'], processed_games_table)
        log_print(f"Game processed successfully: {game['game_uuid']}")

    delete_message(message[0]['ReceiptHandle'], sqs)
    log_print("All games in message processed.")


def main():
    signal.signal(signal.SIGTERM, signal_handler)
    init_engine()
    init_resources()
    
    set_task_protection(True)

    while not shutdown_flag:
        fetch_message()
        if not message:
            shutdown()
            break

        process_message(message, engine, player_stats_table, processed_games_table, sqs)
    
        engine.quit()
        log_print('TASK COMPLETE')

        shutdown()
        break 

if __name__ == '__main__':
    main()