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

def test_add_player(dynamodb_setup):
    """Test adding a new player."""
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
    }], '06-18-2024', '05-18-2024')

    # Check if player was added to TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response, f"Item not found in TrackedPlayers. Response: {response}"
    assert response['Item']['username'] == 'player1'
    assert response['Item']['is_leaderboard_player'] == True

    # Check if player was added to PlayerStats
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response, f"Item not found in PlayerStats. Response: {response}"
    assert response['Item']['username'] == 'player1'
    assert response['Item']['active'] == True

def test_player_inactivity(dynamodb_setup):
    """Test marking a player as inactive due to inactivity."""
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Add a player first
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 1,
        "rating": 2500,
        "player_title": "GM",
        "country": "US",
    }], '06-18-2024', '05-18-2024')

    # Now mark the player as inactive
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], '07-19-2024', '06-19-2024')

    # Check if player was removed from TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'player1'})
    assert 'Item' not in response

    # Check if player was set to inactive in PlayerStats
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['active'] == False

def test_reactivate_player(dynamodb_setup):
    """Test reactivating a player who returns to the leaderboard."""
    dynamodb = dynamodb_setup
    tracked_table = dynamodb.Table('TrackedPlayers')
    stats_table = dynamodb.Table('PlayerStats')

    # Add a player first
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 1,
        "rating": 2500,
        "player_title": "GM",
        "country": "US",
    }], '06-18-2024', '05-18-2024')

    # Mark the player as inactive
    update_player_dbs('TrackedPlayers', 'PlayerStats', [], '07-19-2024', '06-19-2024')

    # Reactivate the player
    update_player_dbs('TrackedPlayers', 'PlayerStats', [{
        "username": "player1",
        "player_name": "Player One",
        "player_rank": 2,
        "rating": 2480,
        "player_title": "GM",
        "country": "US",
    }], '08-20-2024', '07-20-2024')

    # Check if player was re-added to TrackedPlayers
    response = tracked_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'player1'
    assert response['Item']['is_leaderboard_player'] == True

    # Check if player was set back to active in PlayerStats
    response = stats_table.get_item(Key={'username': 'player1'})
    assert 'Item' in response
    assert response['Item']['username'] == 'player1'
    assert response['Item']['active'] == True
    assert response['Item']['player_rank'] == 2  # Check if data was updated
    assert response['Item']['rating'] == 2480



