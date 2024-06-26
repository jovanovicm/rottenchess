import pytest
import boto3
import chess
import chess.engine
from moto import mock_aws
from datetime import datetime
import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis.analysis import process_message, update_player_stats, analyze_moves

@pytest.fixture(scope="module")
def chess_engine():
    if os.getenv('CI', 'false').lower() == 'true':
        path = '/usr/games/stockfish'
    else:
        path = 'stockfish/stockfish-windows-x86-64-avx2.exe'

    engine = chess.engine.SimpleEngine.popen_uci(path)
    yield engine

    engine.quit()

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture(scope="function")
def dynamodb(aws_credentials):
    with mock_aws():
        yield boto3.resource('dynamodb', region_name='us-east-1')

@pytest.fixture(scope="function")
def dynamodb_table(dynamodb):
    table = dynamodb.create_table(
        TableName='PlayerStats',
        KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
    )
    yield table

def test_update_player_stats(dynamodb_table):
    player = "test_player"
    stats = {"inaccuracies": 2, "mistakes": 1, "blunders": 0}
    year = "y2024"
    month = "m01"
    game_info = {
        "url": "https://lichess.org/test_game",
        "magnitude": 4,
        "stats": stats
    }

    update_player_stats(player, stats, year, month, game_info, dynamodb_table, 1)

    response = dynamodb_table.get_item(Key={'username': player})
    assert 'Item' in response
    player_data = response['Item']

    assert player_data['game_stats'][year]['player_total'] == stats
    assert player_data['game_stats'][year][month]['player_total'] == stats
    assert player_data['game_stats'][year]['total_games'] == 1
    assert player_data['game_stats'][year][month]['total_games'] == 1
    assert player_data['game_stats'][year]['worst_game'] == game_info
    assert player_data['game_stats'][year][month]['worst_game'] == game_info

def test_analyze_moves(chess_engine):
    board = chess.Board()
    moves = ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]  # Scholar's mate

    stats = analyze_moves(moves, chess_engine, board)

    assert stats['white']['blunders'] == 0
    assert stats['black']['blunders'] >= 1  # The final move should be considered a blunder

def test_process_message(dynamodb_table, chess_engine):
    players = ['player1', 'player2']
    for player in players:
        dynamodb_table.put_item(Item={'username': player, 'game_stats': {}})

    message = {
        'Body': json.dumps([{
            "game_uuid": "test-game-1",
            "white": "player1",
            "black": "player2",
            "moves": "e4 e5 Qh5 Nc6 Bc4 Nf6 Qxf7#",
            "end_time": 1717200000,
            "game_url": "https://lichess.org/test-game-1"
        }])
    }

    end_time = datetime.fromtimestamp(1717200000)

    process_message(message, chess_engine, dynamodb_table)

    for player in ["player1", "player2"]:
        response = dynamodb_table.get_item(Key={'username': player})
        assert 'Item' in response
        player_data = response['Item']
        
        year = f"y{end_time.year}"
        month = f"m{end_time.month:02}"
        
        assert 'game_stats' in player_data
        assert year in player_data['game_stats']
        assert month in player_data['game_stats'][year]
        assert 'total_games' in player_data['game_stats'][year]
        assert player_data['game_stats'][year]['total_games'] == 1
        assert 'worst_game' in player_data['game_stats'][year]
        assert 'total_games' in player_data['game_stats'][year][month]
        assert player_data['game_stats'][year][month]['total_games'] == 1
        assert 'worst_game' in player_data['game_stats'][year][month]