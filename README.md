# Rotten Chess 🤢
### ~~What is Rotten Chess?~~ What will Rotten Chess become?
Rotten chess will be a leaderboard website tracking the number of inaccuracies, mistakes, and blunders that top players make in their games on chess websites. 
Considering how good these players are, it's humourous to see how many mistakes are made in low time formats.

### How does Rotten Chess work?
Rotten Chess tracks games on **Chess.com** from players in the **Top 50 leaderboard for Blitz** as well as some selected chess personalities like [GothamChess](https://www.youtube.com/channel/UCQHX6ViZmPsWiYSFAyS0a3Q). 
Blitz was selected as it is the most popular chess format on the website among top players.
#### Importing Games
To import games from Chess.com, the Lambda function `import_player_games` is used to gather the games via calls to the Chess.com API. In these calls, the players from the Top 50 leaderboard in Blitz are referenced, and other relevant player information is saved in a **S3** as a JSON file which is referenced later for use in the website. A JSON file containing the tracked chess personalities is also referenced in these API calls. 

These games are imported in JSON format to a DyanmoDB in the following format:
```
    {
        "game_uuid": "c189b116-1d45-11ef-855f-6cfe544c0428", # Primary Key
        "black": {
            "username": "RantomOpening" 
        },
        "end_time": 1716937572,
        "game_url": "https://www.chess.com/game/live/110676101507", 
        "moves": "e4 c5 a3 e6 ...",
        "time_class": "blitz",
        "white": {
            "username": "GothamChess" 
        }
    }
...
```

Once here, the **Simple Queue Service (SQS)** is utilized to gather games in batches using the `enqueue_dynamodb_items` function to prepare games for processing.
#### Provisioning / Deprovisioning PrivateLinks
To save on costs, PrivateLinks for services like the **Elastic Container Registry (ECR)**, and **CloudWatch** are provisioned using the `provision_privatelinks` function only when needed. After all processing is complete, these PrivateLinks are deprovisioned using the `deprovision_privatelinks` function. This results in a **83% lower cost** associated with PrivateLinks.
#### Processing Games
The **Elastic Container Service (ECS)** is used to deploy multiple **Docker Containers**, each containing the **Stockfish chess engine** and a script utilizing the engine to analyze games to gather the numbers of inaccuracies, mistakes, and blunders.
To determine these metrics, Stockfish analyzes each move in a game at a **depth of 20** to determine the centipawn value. This value is put through a function used by Lichess to determine the change of winning percentage for each player. 
By referencing the percentage before and after a move is made by a player, the change in percentage value determines what a move is classified as.

To start the analysis, the Docker Containers grab messages from the queue and run the game moves through the script located on the image.
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


