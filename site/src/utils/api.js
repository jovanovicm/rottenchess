import { useState, useCallback} from 'react';

function useApi() {
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch the list of all players
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

  // Fetch stats for a batch of usernames
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

      // Ensure that data is an array
      if (!Array.isArray(data)) {
        throw new Error('Invalid data format received from server');
      }

      return data;
    } catch (error) {
      console.error('Error fetching players batch:', error);
      return null;
    }
  }, []);

  // Update the leaderboard data
  const updateLeaderboard = useCallback(async (year, month) => {
    setIsLoading(true);
    const playersList = await fetchPlayersList();
    if (!playersList) {
      console.error('Failed to fetch players list');
      setIsLoading(false);
      return;
    }

    const allPlayers = [
      ...playersList.leaderboard_players.active,
      ...playersList.personality_players,
    ];

    // Split the usernames into batches
    const batches = [];
    for (let i = 0; i < allPlayers.length; i += 50) {
      batches.push(allPlayers.slice(i, i + 50));
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

    // Process the player data
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

      return {
        ...player,
        stats,
        totalGames,
      };
    });

    setLeaderboardData(processedData);
    setIsLoading(false);
  }, [fetchPlayersList, fetchPlayersBatch]);

  return { leaderboardData, isLoading, updateLeaderboard };
}

export default useApi;