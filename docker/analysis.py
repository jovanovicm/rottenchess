import json
import chess
import chess.engine
import math
import boto3
import os

AWS_REGION = os.getenv('AWS_REGION')
QUEUE_URL = os.getenv('SQS_QUEUE_URL')

ENGINE_PATH = '/usr/games/stockfish'
engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)

sqs = boto3.client('sqs', 
                   region_name=AWS_REGION)

def log_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

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
        VisibilityTimeout=300
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

        if win_prob_change >= 0.3:
            stats[player]['blunders'] += 1
        elif win_prob_change >= 0.2:
            stats[player]['mistakes'] += 1
        elif win_prob_change >= 0.1:
            stats[player]['inaccuracies'] += 1

    return stats

def process_message(message):
    games = json.loads(message['Body'])
    player_stats = {}
    board = chess.Board()
    for game in games:
        board.reset()
        moves = game['moves'].split()
        log_print(f"Processing game: {game['game_id']}")
        game_stats = analyze_moves(moves, engine, board)
        if game_stats is None:
            continue

        for color, player in game['players'].items():
            if player not in player_stats:
                player_stats[player] = {'inaccuracies': 0, 'mistakes': 0, 'blunders': 0}
            for key in game_stats[color]:
                player_stats[player][key] += game_stats[color][key]
    return player_stats

def main():
    messages = fetch_messages()
    for message in messages:
        stats = process_message(message)
        log_print(json.dumps(stats, indent=4))
        delete_message(message['ReceiptHandle'])
    
    engine.quit()
    log_print('TASK COMPLETE')
    decrease_task_count('rotten-chess-game-analysis', 'rotten-chess-ecs-service')

if __name__ == '__main__':
    main()

