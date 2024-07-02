import os
import pytest
import boto3
from moto import mock_aws
from functions.import_player_games.import_player_games import update_player_dbs

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture
def aws(aws_credentials):
    with mock_aws():
        yield boto3

@pytest.fixture
def dynamodb_setup(aws):
    # Create DynamoDB tables required for the tests
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    dynamodb.create_table(
        TableName='TrackedPlayers',
        KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )
    dynamodb.create_table(
        TableName='PlayerStats',
        KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )
    yield dynamodb

def test_add_leaderboard_player(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 1,
        "rating": 2500,
        "player_title": "GM",
        "country": "US",
    }], [], '06-18-2024', '05-18-2024')

    # Check if player was added to TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'player1'
    assert response['Item']['is_leaderboard_player'] == True
    assert 'last_seen' in response['Item']

    # Check if player was added to PlayerStats
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'player1'
    assert response['Item']['active'] == True
    assert 'player_rank' in response['Item']

def test_add_chess_personality(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [{
        "username": "personality1",
        "player_name": "Personality One",
        "rating": 2200,
        "player_title": "IM",
        "country": "CA",
    }], '06-18-2024', '05-18-2024')

    # Check if personality was added to TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'personality1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality1'
    assert response['Item']['is_leaderboard_player'] == False
    assert 'last_seen' not in response['Item']

    # Check if personality was added to PlayerStats
    response = stats_table.get_item(Key={'username': 'personality1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality1'
    assert 'active' not in response['Item']
    assert 'player_rank' not in response['Item']

def test_update_chess_personality(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Add a chess personality
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [{
        "username": "personality1",
        "player_name": "Personality One",
        "rating": 2200,
        "player_title": "IM",
        "country": "CA",
    }], '06-18-2024', '05-18-2024')

    # Update the chess personality
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [{
        "username": "personality1",
        "player_name": "Personality One",
        "rating": 2300,
        "player_title": "IM",
        "country": "CA",
    }], '06-19-2024', '05-19-2024')

    # Check if personality is still not a leaderboard player
    response = tracked_table.get_item(Key={'username': 'personality1'})
    assert response['Item']['is_leaderboard_player'] == False

    # Check if personality's rating was updated
    response = stats_table.get_item(Key={'username': 'personality1'})
    assert response['Item']['rating'] == 2300

def test_player_inactivity(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Add a leaderboard player
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 1,
        "rating": 2500,
        "player_title": "GM",
        "country": "US",
    }], [], '06-18-2024', '05-18-2024')

    # Simulate being outside of leaderboard for 30 days
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [], '07-19-2024', '06-19-2024')

    # Check if player was removed from TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'player1'})
    assert 'Item' not in response

    # Check if player is still in PlayerStats but inactive
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['active'] == False

def test_player_leaves_leaderboard(dynamodb_setup):
    dynamodb = dynamodb_setup
    stats_table = dynamodb.Table('PlayerStats')

    # Add a player as an active leaderboard member
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 1,
        "rating": 2500,
        "player_title": "GM",
        "country": "US",
    }], [], '06-18-2024', '05-18-2024')

    # Simulate the player not being on the leaderboard anymore
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [], '06-19-2024', '05-19-2024')

    # Verify the player is marked as inactive in the PlayerStats table
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['active'] == False
    assert response['Item']['is_leaderboard_player'] == True

def test_chess_personality_persistence(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Add a chess personality
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [{
        "username": "personality1",
        "player_name": "Personality One",
        "rating": 2200,
        "player_title": "IM",
        "country": "CA",
    }], '06-18-2024', '05-18-2024')

    # Simulate multiple updates
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [], f'06-19-2024', f'05-19-2024')

    # Check if personality is still in TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'personality1'})
    assert 'Item' in response
    assert response['Item']['is_leaderboard_player'] == False

    # Check if personality is still in PlayerStats
    response = stats_table.get_item(Key={'username': 'personality1'})
    assert 'Item' in response
    assert 'active' not in response['Item']

def test_game_stats_persistence(dynamodb_setup):
    dynamodb = dynamodb_setup
    stats_table = dynamodb.Table('PlayerStats')

    # Sample game_stats object
    game_stats = {
        "y2024": {
            "m06": {
                "player_total": {
                    "blunders": 2,
                    "inaccuracies": 13,
                    "mistakes": 5
                },
                "total_games": 5,
                "worst_game": {
                    "game_url": "https://www.chess.com/game/live/113170760949",
                    "magnitude": 13,
                    "stats": {
                        "blunders": 1,
                        "inaccuracies": 6,
                        "mistakes": 2
                    }
                }
            },
            "player_total": {
                "blunders": 2,
                "inaccuracies": 13,
                "mistakes": 5
            },
            "total_games": 5,
            "worst_game": {
                "game_url": "https://www.chess.com/game/live/113170760949",
                "magnitude": 13,
                "stats": {
                    "blunders": 1,
                    "inaccuracies": 6,
                    "mistakes": 2
                }
            }
        }
    }

    # Add a player with game_stats to the PlayerStats table
    stats_table.put_item(Item={
        "username": "player_with_stats",
        "player_name": "Player With Stats",
        "rating": 2000,
        "player_title": "FM",
        "country": "US",
        "is_leaderboard_player": True,
        "active": True,
        "game_stats": game_stats
    })

    # Run update_player_dbs
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player_with_stats",
        "player_name": "Player With Stats",
        "player_rank": 50,
        "rating": 2050,
        "player_title": "FM",
        "country": "US",
    }], [], '06-20-2024', '05-20-2024')

    # Check if player's data is still in PlayerStats and game_stats is unchanged
    response = stats_table.get_item(Key={'username': 'player_with_stats'})
    assert 'Item' in response
    assert response['Item']['username'] == 'player_with_stats'
    assert response['Item']['rating'] == 2050
    assert response['Item']['player_rank'] == 50
    assert 'game_stats' in response['Item']
    assert response['Item']['game_stats'] == game_stats

def test_personality_to_leaderboard_player(dynamodb_setup):
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Step 1: Add the player as a personality
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], [{
        "username": "personality_player",
        "player_name": "Personality Player",
        "rating": 2200,
        "player_title": "IM",
        "country": "CA",
    }], '06-18-2024', '05-18-2024')

    # Check if personality was added to TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'personality_player'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality_player'
    assert response['Item']['is_leaderboard_player'] == False

    # Check if personality was added to PlayerStats
    response = stats_table.get_item(Key={'username': 'personality_player'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality_player'
    assert 'active' not in response['Item']
    assert 'player_rank' not in response['Item']

    # Step 2: Update the player to a leaderboard player
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "personality_player",
        "player_name": "Personality Player",
        "player_rank": 10,
        "rating": 2300,
        "player_title": "IM",
        "country": "CA",
    }], [], '06-19-2024', '05-19-2024')

    # Check if the player is now a leaderboard player in TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'personality_player'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality_player'
    assert response['Item']['is_leaderboard_player'] == True
    assert response['Item']['last_seen'] == '06-19-2024'

    # Check if the player's stats are updated in PlayerStats
    response = stats_table.get_item(Key={'username': 'personality_player'})
    assert 'Item' in response
    assert response['Item']['username'] == 'personality_player'
    assert response['Item']['rating'] == 2300
    assert response['Item']['player_rank'] == 10
    assert response['Item']['is_leaderboard_player'] == True
    assert response['Item']['active'] == True