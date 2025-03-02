import json
import chess
import chess.engine
import math
import boto3
import os
from datetime import timezone, datetime
import signal
import sys

AWS_REGION = os.getenv('AWS_REGION')
QUEUE_URL = os.getenv('SQS_QUEUE_URL')
PLAYER_STATS_TABLE = os.getenv('PLAYER_STATS_TABLE')
PROCESSED_GAMES_TABLE = os.getenv('PROCESSED_GAMES_TABLE')

shutdown_flag = False
message = None

def log_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def init_resources():
    global sqs, player_stats_table, processed_games_table

    try:
        log_print("Initializing SQS client in region:", AWS_REGION)
        sqs = boto3.client('sqs', region_name=AWS_REGION)
        log_print("SQS client created:", sqs)
    except Exception as e:
        log_print("Error initializing SQS client:", str(e))

    try:
        log_print("Initializing DynamoDB resource in region:", AWS_REGION)
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        player_stats_table = dynamodb.Table(PLAYER_STATS_TABLE)
        processed_games_table = dynamodb.Table(PROCESSED_GAMES_TABLE)
        log_print("DynamoDB tables initialized: PLAYER_STATS_TABLE =", PLAYER_STATS_TABLE,
                  "PROCESSED_GAMES_TABLE =", PROCESSED_GAMES_TABLE)
    except Exception as e:
        log_print("Error initializing DynamoDB resource:", str(e))

def init_engine(path='/usr/local/bin/stockfish'):
    global engine
    try:
        log_print("Initializing chess engine from:", path)
        engine = chess.engine.SimpleEngine.popen_uci(path)
        log_print("Chess engine initialized.")
    except Exception as e:
        log_print("Error initializing chess engine:", str(e))
        raise

def signal_handler(signum, frame):
    global shutdown_flag, message
    log_print("Signal handler invoked with signal:", signum)
    try:
        if message and len(message) > 0:
            log_print("Changing message visibility for receipt handle:",
                      message[0]['ReceiptHandle'])
            response = sqs.change_message_visibility(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message[0]['ReceiptHandle'],
                VisibilityTimeout=0
            )
            log_print("ChangeMessageVisibility response:", response)
    except IndexError:
        log_print("Error: message list is empty during shutdown.")
    except Exception as e:
        log_print("Error during message visibility change:", str(e))
    
    shutdown_flag = True
    log_print("Shutdown signal received. Shutting down...")

def mark_game_as_processed(message_id, game_uuid, processed_games_table):
    try:
        log_print(f"Marking game {game_uuid} as processed for message {message_id}")
        response = processed_games_table.update_item(
            Key={'message_id': message_id},
            UpdateExpression="SET game_ids = list_append(if_not_exists(game_ids, :empty_list), :game_uuid)",
            ExpressionAttributeValues={
                ':empty_list': [],
                ':game_uuid': [game_uuid]
            }
        )
        log_print("mark_game_as_processed response:", response)
    except Exception as e:
        log_print("Error in mark_game_as_processed:", str(e))

def get_processed_games(message_id, processed_games_table):
    try:
        log_print("Getting list of processed games for message ID:", message_id)
        response = processed_games_table.get_item(Key={'message_id': message_id})
        log_print("DynamoDB get_item response:", response)
    except Exception as e:
        log_print("Error fetching processed games for message", message_id, ":", str(e))
        return []
    processed_games = response.get('Item', {}).get('game_ids', [])
    log_print("Processed games:", processed_games)
    return processed_games

def update_player_stats(player, stats, year, month, game_info, player_stats_table, total_games_increment):
    keys = {'username': player}
    log_print(f"Updating stats for player {player}")

    # Initialize paths for maps
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

    for expr in initialize_map_paths:
        try:
            log_print(f"Updating (map init) for {player} using expression: {expr}")
            response = player_stats_table.update_item(
                Key=keys,
                UpdateExpression=expr,
                ExpressionAttributeValues={":empty_map": {}}
            )
            log_print("Map initialization response:", response)
        except Exception as e:
            log_print("Error during map initialization for", player, ":", str(e))

    for expr in initialize_zero_paths:
        try:
            log_print(f"Updating (zero init) for {player} using expression: {expr}")
            response = player_stats_table.update_item(
                Key=keys,
                UpdateExpression=expr,
                ExpressionAttributeValues={":zero": 0}
            )
            log_print("Zero initialization response:", response)
        except Exception as e:
            log_print("Error during zero initialization for", player, ":", str(e))

    try:
        update_expression = f"ADD game_stats.{year}.total_games :inc_games, game_stats.{year}.{month}.total_games :inc_games"
        log_print(f"Updating total_games for {player} using expression: {update_expression}")
        response = player_stats_table.update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues={":inc_games": total_games_increment}
        )
        log_print("Total games update response:", response)
    except Exception as e:
        log_print("Error updating total_games for", player, ":", str(e))

    for stat, increment in stats.items():
        try:
            yearly_path = f"game_stats.{year}.player_total.{stat}"
            monthly_path = f"game_stats.{year}.{month}.player_total.{stat}"
            update_expression = f"ADD {yearly_path} :inc, {monthly_path} :inc"
            log_print(f"Updating stat '{stat}' for {player} using expression: {update_expression}")
            response = player_stats_table.update_item(
                Key=keys,
                UpdateExpression=update_expression,
                ExpressionAttributeValues={":inc": increment}
            )
            log_print(f"Update response for stat '{stat}' for {player}:", response)
        except Exception as e:
            log_print(f"Error updating stat '{stat}' for {player}:", str(e))

    try:
        log_print(f"Fetching current stats for {player}")
        response = player_stats_table.get_item(Key=keys)
        log_print("Current stats get_item response:", response)
    except Exception as e:
        log_print("Error fetching current stats for", player, ":", str(e))
        response = {}
    item = response.get('Item', {})
    game_stats = item.get('game_stats', {})
    year_stats = game_stats.get(year, {})
    month_stats = year_stats.get(month, {})

    yearly_worst_game = year_stats.get('worst_game', {'magnitude': -1})
    monthly_worst_game = month_stats.get('worst_game', {'magnitude': -1})

    if game_info['magnitude'] > yearly_worst_game.get('magnitude', -1):
        try:
            update_expression = f"SET game_stats.{year}.worst_game = :game_info"
            log_print(f"Updating yearly worst game for {player} using expression: {update_expression}")
            response = player_stats_table.update_item(
                Key=keys,
                UpdateExpression=update_expression,
                ExpressionAttributeValues={":game_info": game_info}
            )
            log_print("Yearly worst game update response:", response)
        except Exception as e:
            log_print("Error updating yearly worst game for", player, ":", str(e))

    if game_info['magnitude'] > monthly_worst_game.get('magnitude', -1):
        try:
            update_expression = f"SET game_stats.{year}.{month}.worst_game = :game_info"
            log_print(f"Updating monthly worst game for {player} using expression: {update_expression}")
            response = player_stats_table.update_item(
                Key=keys,
                UpdateExpression=update_expression,
                ExpressionAttributeValues={":game_info": game_info}
            )
            log_print("Monthly worst game update response:", response)
        except Exception as e:
            log_print("Error updating monthly worst game for", player, ":", str(e))

    log_print(f"Updated stats for {player} in {month}/{year}: {stats}")

def fetch_message():
    global message
    try:
        log_print("Fetching message from SQS. Queue URL:", QUEUE_URL)
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
            VisibilityTimeout=7200  # 2 hours
        )
        log_print("SQS receive_message response:", response)
    except Exception as e:
        log_print("Error fetching message from SQS:", str(e))
        response = {}
    message = response.get('Messages', [])
    if not message:
        log_print("No messages received from SQS.")

def delete_message(receipt_handle, sqs):
    try:
        log_print("Deleting SQS message with receipt handle:", receipt_handle)
        response = sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        log_print("SQS delete_message response:", response)
    except Exception as e:
        log_print("Error deleting SQS message:", str(e))

def analyze_moves(moves, engine, board):
    stats = {'white': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0},
             'black': {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0}}

    def winning_chances(cp):
        MULTIPLIER = -0.00368208
        return 1 / (1 + math.exp(MULTIPLIER * cp))

    for i, move_san in enumerate(moves):
        player = 'white' if i % 2 == 0 else 'black'
        try:
            log_print(f"Analyzing move {i+1} for {player}: {move_san}")
            info_before = engine.analyse(board, chess.engine.Limit(depth=20))
            score_before = info_before['score']
            cp_before = score_before.white().score(mate_score=10000) if player == 'white' else score_before.black().score(mate_score=10000)
            
            move = board.parse_san(move_san)
            board.push(move)
            log_print("Applied move:", move_san)
            
            info_after = engine.analyse(board, chess.engine.Limit(depth=20))
            score_after = info_after['score']
            cp_after = int(score_after.white().score(mate_score=10000)) if player == 'white' else int(score_after.black().score(mate_score=10000))
            
            wp_before = winning_chances(cp_before)
            wp_after = winning_chances(cp_after)
            win_prob_change = abs(wp_after - wp_before)
            log_print(f"Win probability change for {player}: {win_prob_change:.4f}")
            
            if win_prob_change >= 0.2:
                stats[player]['blunders'] += 1
            elif win_prob_change >= 0.1:
                stats[player]['mistakes'] += 1
            elif win_prob_change >= 0.05:
                stats[player]['inaccuracies'] += 1
        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
            log_print("Move error for", move_san, ":", str(e))
            raise
    return stats

def process_message(message, engine, player_stats_table, processed_games_table, sqs):
    message_id = message[0]['MessageId']
    log_print("Processing message ID:", message_id)
    try:
        games = json.loads(message[0]['Body'])
        log_print("Parsed message body into games:", games)
    except Exception as e:
        log_print("Error parsing message body:", str(e))
        return
    board = chess.Board()
    processed_games = get_processed_games(message_id, processed_games_table)

    for game in games:
        if game['game_uuid'] in processed_games:
            log_print("Skipping already processed game:", game["game_uuid"])
            continue

        board.reset()
        moves = game['moves'].split()
        end_time = datetime.fromtimestamp(game['end_time'], timezone.utc)
        year = f'y{end_time.year}'
        month = f'm{end_time.month:02}'
        
        log_print("Processing game:", game['game_uuid'])
        try:
            game_stats = analyze_moves(moves, engine, board)
            log_print("Analysis complete for game:", game['game_uuid'], "Stats:", game_stats)
        except Exception as e:
            log_print("Error analyzing game", game['game_uuid'], ":", str(e))
            continue

        players = {'white': game['white'], 'black': game['black']}
        for colour, player in players.items():
            try:
                log_print("Fetching stats for player:", player)
                response = player_stats_table.get_item(Key={'username': player})
                log_print("Get_item response for", player, ":", response)
            except Exception as e:
                log_print("Error fetching player", player, ":", str(e))
                continue

            if 'Item' not in response:
                log_print(f"Player {player} not found in database. Skipping...")
                continue

            current_stats = game_stats[colour]
            game_magnitude = current_stats['blunders'] * 3 + current_stats['mistakes'] * 2 + current_stats['inaccuracies']
            game_info = {
                'game_url': game['game_url'],
                'magnitude': game_magnitude,
                'stats': current_stats
            }
            update_player_stats(player, current_stats, year, month, game_info, player_stats_table, 1)
        
        mark_game_as_processed(message_id, game['game_uuid'], processed_games_table)
        log_print("Game processed successfully:", game['game_uuid'])
    
    delete_message(message[0]['ReceiptHandle'], sqs)
    log_print("All games in message processed.")

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    init_engine()
    init_resources()

    while not shutdown_flag:
        fetch_message()
        if not message:
            log_print("No messages fetched. Exiting main loop.")
            break

        process_message(message, engine, player_stats_table, processed_games_table, sqs)

        try:
            engine.quit()
            log_print("Chess engine quit successfully.")
        except Exception as e:
            log_print("Error quitting chess engine:", str(e))
        log_print("TASK COMPLETE")
        break

    log_print("Exiting process now.")
    sys.exit(0)

if __name__ == '__main__':
    main()