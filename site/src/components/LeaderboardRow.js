import React from 'react';

const customTitles = {
  "markoj000": "Dev",
  "brydog123": "Dev",
};

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
  const { stats, totalGames, username } = player;
  const rpg = calculateRPG(stats, totalGames);
  const customTitle = customTitles[username];
  const normalTitle = player.player_title;

  // Use historical data when available
  const displayRank = player.historicalRank !== undefined ? player.historicalRank : player.player_rank;
  const displayRating = player.historicalRating !== undefined ? player.historicalRating : player.rating;

  return (
    <tr data-category={player.is_leaderboard_player ? 'top50' : 'personality'}
        className={player.is_personality_player ? 'highlight-personality' : ''}>
      {currentFilter === 'top50' && <td>{displayRank}</td>}
      <td>
        {customTitle && 
          <div className="custom-title">
            {customTitle}
          </div>
        }
        {normalTitle && normalTitle !== 'None' && 
          <div className="leaderboard-chess-title">
            {normalTitle}
          </div>
        }
        <a href={`https://www.chess.com/member/${username}`} target="_blank" rel="noopener noreferrer" className="username">
          {player.player_name}
        </a>
        <div className={`country-flag ${getCountryCodeClass(player.country)}`}></div>
      </td>
      <td className="rating-column">{displayRating}</td>
      <td><strong>{rpg.toFixed(2)}</strong></td>
      <td>{totalGames || 0}</td>
      <td>{stats.blunders || 0}</td>
      <td>{stats.mistakes || 0}</td>
      <td>{stats.inaccuracies || 0}</td>
    </tr>
  );
}

export default LeaderboardRow;