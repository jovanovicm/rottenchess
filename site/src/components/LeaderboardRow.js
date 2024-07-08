import React from 'react';

const LeaderboardRow = ({ player }) => {
  const { stats, totalGames } = getPlayerStats(player);
  const rpg = calculateRPG(stats, totalGames);

  const countryCodeClass = getCountryCodeClass(player.country);

  return (
    <tr data-category={player.is_leaderboard_player ? 'top50' : 'personality'}>
      <td>{player.player_rank}</td>
      <td>
        <div className="leaderboard-chess-title">{player.player_title}</div>
        <a href={`https://www.chess.com/member/${player.username}`} target="_blank" rel="noopener noreferrer">{player.player_name}</a>
        <div className={`country-flag ${countryCodeClass}`}></div>
      </td>
      <td>{player.rating}</td>
      <td><strong>{rpg.toFixed(2)}</strong></td>
      <td>{totalGames || 0}</td>
      <td>{stats.blunders || 0}</td>
      <td>{stats.mistakes || 0}</td>
      <td>{stats.inaccuracies || 0}</td>
    </tr>
  );
}

const getPlayerStats = (player) => {
  let stats = {};
  let totalGames = 0;
  const currentMonth = new Date().getMonth().toString().padStart(2, "0");
  const currentYear = new Date().getFullYear().toString();

  if (currentMonth === "all") {
    stats = player.game_stats?.[`y${currentYear}`]?.player_total || {};
    totalGames = player.game_stats?.[`y${currentYear}`]?.total_games || 0;
  } else {
    stats = player.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]?.player_total || {};
    totalGames = player.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]?.total_games || 0;
  }

  return { stats, totalGames };
}

const calculateRPG = (stats, totalGames) => {
  if (!totalGames || totalGames === 0) return 0;
  return (((stats.blunders || 0) * 3) + ((stats.mistakes || 0) * 2) + (stats.inaccuracies || 0)) / totalGames;
}

const getCountryCodeClass = (country) => {
  return country ? `country-${country.toLowerCase()}` : '';
}

export default LeaderboardRow;