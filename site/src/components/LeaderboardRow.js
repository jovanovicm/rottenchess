import React from 'react';

function getCountryCodeClass(country) {
  return `country-${country.toLowerCase()}`;
}

function calculateRPG(stats, totalGames) {
  if (!totalGames || totalGames === 0) return 0;
  return (
    (((stats.blunders || 0) * 3) +
      ((stats.mistakes || 0) * 2) +
      (stats.inaccuracies || 0)) /
    totalGames
  );
}

function LeaderboardRow({ player, currentFilter }) {
  const { stats, totalGames } = player;
  const rpg = calculateRPG(stats, totalGames);

  return (
    <tr data-category={player.is_leaderboard_player ? 'top50' : 'personality'}>
      {currentFilter === 'top50' && <td>{player.player_rank}</td>}
      <td>
        {player.player_title !== 'None' && <div className="leaderboard-chess-title">{player.player_title}</div>}
        <a href={`https://www.chess.com/member/${player.username}`} target="_blank" rel="noopener noreferrer" className="username">
          {player.player_name}
        </a>
        <div className={`country-flag ${getCountryCodeClass(player.country)}`}></div>
      </td>
      <td className="rating-column">{player.rating}</td>
      <td><strong>{rpg.toFixed(2)}</strong></td>
      <td>{totalGames || 0}</td>
      <td>{stats.blunders || 0}</td>
      <td>{stats.mistakes || 0}</td>
      <td>{stats.inaccuracies || 0}</td>
    </tr>
  );
}

export default LeaderboardRow;