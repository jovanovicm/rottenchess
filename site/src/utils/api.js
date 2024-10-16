import { useState, useCallback } from 'react';

function useApi() {
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [leaderboardHistory, setLeaderboardHistory] = useState(null);

  const fetchPlayersList = useCallback(async () => {
    try {
      const response = await fetch('https://api.rottenchess.com/players?list=true');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching players list:', error);
      return null;
    }
  }, []);

  const fetchPlayersBatch = useCallback(async (usernames) => {
    try {
      const usernamesParam = usernames.join(',');
      const response = await fetch(
        `https://api.rottenchess.com/players?usernames=${encodeURIComponent(usernamesParam)}`
      );
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error('Invalid data format received from server');
      }

      return data;
    } catch (error) {
      console.error('Error fetching players batch:', error);
      return null;
    }
  }, []);

  const fetchLeaderboardHistory = useCallback(async (year, month) => {
    try {
      const response = await fetch(`https://api.rottenchess.com/leaderboard?year=${year}&month=${month}`);
      if (!response.ok) {
        // If the response is 404, it means there's no historical data for this month
        if (response.status === 404) {
          console.warn(`No leaderboard history found for ${year}/${month}`);
          setLeaderboardHistory(null);
          return null;
        } else {
          throw new Error('Network response was not ok');
        }
      }
      const data = await response.json();
      setLeaderboardHistory(data);
      return data;
    } catch (error) {
      console.error('Error fetching leaderboard history:', error);
      return null;
    }
  }, []);

  const updateLeaderboard = useCallback(async (year, month) => {
    setIsLoading(true);

    const history = await fetchLeaderboardHistory(year, month);

    let usernamesToFetch = [];
    let leaderboardPlayersSet = new Set();
    let personalityPlayersSet = new Set();

    // Fetch players list to get personality players
    const playersList = await fetchPlayersList();
    if (!playersList) {
      console.error('Failed to fetch players list');
      setIsLoading(false);
      return;
    }
    if (playersList.personality_players) {
      personalityPlayersSet = new Set(playersList.personality_players);
    }

    if (history && history.players) {
      // Use usernames from the historical data
      usernamesToFetch = Object.keys(history.players);

      // Exclude personality players from leaderboardPlayersSet
      const leaderboardUsernames = usernamesToFetch.filter(
        (username) => !personalityPlayersSet.has(username)
      );
      leaderboardPlayersSet = new Set(leaderboardUsernames);

      // Include personality players in usernamesToFetch
      usernamesToFetch = usernamesToFetch.concat(playersList.personality_players);
    } else {
      // Fallback to current players list
      usernamesToFetch = [
        ...playersList.leaderboard_players.active,
        ...playersList.personality_players,
      ];
      leaderboardPlayersSet = new Set(playersList.leaderboard_players.active);
    }

    // Remove duplicates
    usernamesToFetch = [...new Set(usernamesToFetch)];

    // Fetch player data in batches
    const batches = [];
    for (let i = 0; i < usernamesToFetch.length; i += 50) {
      batches.push(usernamesToFetch.slice(i, i + 50));
    }

    let allPlayerData = [];
    for (const batch of batches) {
      const batchData = await fetchPlayersBatch(batch);
      if (Array.isArray(batchData)) {
        allPlayerData = [...allPlayerData, ...batchData];
      } else {
        console.error(`Failed to fetch data for batch: ${batch}`);
      }
    }

    // Process data
    const processedData = allPlayerData.map((player) => {
      let stats = {};
      let totalGames = 0;

      if (month === 'all') {
        stats = player.game_stats?.[`y${year}`]?.player_total || {};
        totalGames = player.game_stats?.[`y${year}`]?.total_games || 0;
      } else {
        stats =
          player.game_stats?.[`y${year}`]?.[`m${month}`]?.player_total || {};
        totalGames =
          player.game_stats?.[`y${year}`]?.[`m${month}`]?.total_games || 0;
      }

      // Handle historical data
      let historicalData = {};
      if (history && history.players && history.players[player.username]) {
        historicalData = history.players[player.username];
      }

      // Set is_leaderboard_player based on historical data or current data
      let isLeaderboardPlayer = leaderboardPlayersSet.has(player.username);

      // Set is_personality_player based on personalityPlayersSet
      let isPersonalityPlayer = personalityPlayersSet.has(player.username);

      return {
        ...player,
        stats,
        totalGames,
        historicalRank: historicalData.player_rank,
        historicalRating: historicalData.rating,
        is_leaderboard_player: isLeaderboardPlayer,
        is_personality_player: isPersonalityPlayer,
      };
    });

    setLeaderboardData(processedData);
    setIsLoading(false);
  }, [fetchPlayersList, fetchPlayersBatch, fetchLeaderboardHistory]);

  return { leaderboardData, isLoading, updateLeaderboard, leaderboardHistory };
}

export default useApi;