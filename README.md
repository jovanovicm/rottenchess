# RottenChess 🤢
### What is RottenChess?
[RottenChess is a leaderboard website](https://www.rottenchess.com) tracking the number of inaccuracies, mistakes, and blunders that top players and chess celebrities make in their most mistake-ridden and **rotten chess** games on **Chess.com** 

The leaderboard is ranked by the average number of **ROTS per Game (RpG)**
- **Blunders** are 3 ROTS 🤮
- **Mistakes** are 2 ROTS 🤢
- **Inaccuracies** are 1 ROTS 🥴


## How does RottenChess work?
RottenChess tracks games on **Chess.com** from players in the **Top 50 leaderboard for Blitz** as well as some selected chess personalities like [GothamChess](https://www.youtube.com/channel/UCQHX6ViZmPsWiYSFAyS0a3Q) and [Alexandra Botez](https://www.youtube.com/channel/UCAn8NrZ-J4CRfwodajqFYoQ).
Blitz was selected as it is the most popular chess format on the website among top players.

### Importing Games
RottenChess tracks games using the Chess.com API. 

The list of players being tracked changes dynamically with how the leaderboard on Chess.com changes. Players who leave the leaderboard will have their games tracked for an additional month to have continuity in their game stats if they happen to return to the leaderboard shortly after. They will be removed from the list of tracked players after a month outside of the leaderboard to limit the amount of individuals being tracked.

RottenChess specifically tracks:
- **Top 50 Blitz Players**: Players ranked in the top 50 in the Blitz category
- **Tracked Personalities and Players**: Curated list of chess personalities and other players of interest ([like myself](https://www.chess.com/member/markoj000))

### Processing Games
Once the Game Imports Table is populated, the Simple Queue Service (SQS) is utilized to gather games in batches to prepare games for processing.

The Elastic Container Service (ECS) is used to deploy multiple Docker Containers. Each Container has:
- **Stockfish 16.1 Chess Engine:** A very strong chess engine
- **analysis.py:** A script utilizing the engine to import and analyze games to gather the number of blunders, mistakes, and inaccuracies

#### Analysis
Docker Containers grab messages from the SQS queue and run the game moves through the script located on the image.
The number of containers deploys one-to-one with the number of messages within the SQS Queue, ensuring that the compute infrastructure scales with the number of games played on any day.
Results are sent to the Player Stats Table.

---
#### Win Percentage Calculation
To determine the move classifications, first a win percentage calculation must happen. Win percentage represents the chances a player has to win a game in a given position. Stockfish analyzes each position in a game at a <ins>Depth of 20</ins> to determine the centipawn value. The centipawn value is used in the following function, which is [used by Lichess](https://lichess.org/page/accuracy), to calculate the win percentage for every position.
```
Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * centipawns)) - 1)
```
> Win Percentage is based on Player ELO. Chess.com uses a closed source dyanmic system called ClassificationV2. Lichess uses an open source static system which uses the formula above which is calculated using games played by 2300 ELO players as a benchmark to determine winning chances.

---
#### Move Classification
By referencing the change in percentage value between positions, we can determine what the move leading to a position is classified as. The following bounds, which are the same bounds [used by Chess.com](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-and-etc), are used for move classification:

```
Blunder = win_prob_change >= 0.2        
Mistake = 0.05 < win_prob_change >= 0.1
Inaccuracy = 0 < win_prob_change >= 0.05
```
> Move classifications may be different than the classifications on Chess.com due to the different methods used to determine win percentages
