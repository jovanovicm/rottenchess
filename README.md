# Rotten Chess 🤢
### ~~What is Rotten Chess?~~ What will Rotten Chess become?
Rotten chess will be a leaderboard website tracking the number of inaccuracies, mistakes, and blunders that top players make in their games on chess websites. 
Considering how good these players are, it's humourous to see how many mistakes are made in low time formats.

### How does Rotten Chess (currently) work?
For early development, Rotten Chess is set up to track games from **Lichess**, but this will change in the future. Currently, **Chess.com** is a much more popular website for top players to use, but they have a terrible API.
Eventually, the project will transition into tracking Chess.com games using their terrible API.

#### Importing Games
To import games from these chess websites, the Lambda function **import_player_games** is deployed to gather the games via calls to the API from a defined list of players found in the leaderboard of a particular chess format. Currently, the list is static, and the script must be ran manually.
Future plans include automating the script calls via a scheduled event, and making the list of players dynamically change with who is currently in the leaderboard. 

These games are imported in JSON format to a DyanmoDB in the following format:
```
{
  "game_id": {
    "maaxk8nW"
  },
  "moves": {
    "g3 c5 Bg2 Nc6 ... "
  },
  "perf": {
    "bullet"
  },
  "players": {
      {
      "black": {
        chesstutorai"
      },
      "white": {
        "mirakel05"
      }
    }
  }
}
```

Once here, the Simple Queue Service (SQS) is utilized to gather games in batches using the **enqueue_dynamodb_items** function to prepare games for processing.

#### Processing Games
The Elastic Container Service (ECS) is used to deploy multiple Docker Containers, each containing the Stockfish chess engine and a script utilizing the engine to analyze games to gather the numbers of inaccuracies, mistakes, and blunders.
To determine these metrics, Stockfish analyzes each move in a game at a depth of 20 to determine the centipawn value. This value is put through a function used by Lichess to determine the change of winning percentage for each player. 
By referencing the respective percentage before and after a move is made by a player, the change in value determines what a move is classified as.

To start the analysis, the docker containers grab messages from the queue and run the game moves through the script located on the image.
The number of containers deployed depends on the number of messages within the SQS Queue ensuring that the compute infrastructure scales with the number of games played on any day. 

The analysis of the games is outputted in the following format:
```
{
  "heisenberg01": {
    "inaccuracies": 5,
    "mistakes": 1,
    "blunders": 1
    },
  "kerryxyn": {
    "inaccuracies": 5,
    "mistakes": 0,
    "blunders": 1
    },
  ...
}
```


