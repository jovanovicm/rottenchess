import React from 'react';
import LeaderboardRow from './LeaderboardRow';
import Loading from './Loading';

const Leaderboard = ({ players, filter, loading }) => {
  const filteredPlayers = players.filter(player => {
    const category = player.is_leaderboard_player ? 'top50' : 'personality';
    return filter === 'all' || category === filter;
  });

  return (
    <div>
      {loading ? <Loading /> : (
        <table className="leaderboard">
          <thead>
            <tr>
              <th className="ranking-column">Ranking</th>
              <th>Username</th>
              <th>Rating</th>
              <th>RpG</th>
              <th>Games played</th>
              <th>Blunders</th>
              <th>Mistakes</th>
              <th>Inaccuracies</th>
            </tr>
          </thead>
          <tbody>
            {filteredPlayers.map(player => (
              <LeaderboardRow key={player.username} player={player} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Leaderboard;