import { useState, useCallback} from 'react';

function useApi() {
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchPlayersList = useCallback(async () => {
    try {
      const response = await fetch('https://api.rottenchess.com/players');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching players list:', error);
      return null;
    }
  }, []);

  const fetchPlayersBatch = useCallback(async (usernames) => {
    try {
      const response = await fetch('https://api.rottenchess.com/players/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ usernames }),
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching players batch:', error);
      return null;
    }
  }, []);

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

    const batches = [];
    for (let i = 0; i < allPlayers.length; i += 50) {
      batches.push(allPlayers.slice(i, i + 50));
    }

    let allPlayerData = [];
    for (const batch of batches) {
      const batchData = await fetchPlayersBatch(batch);
      if (batchData) {
        allPlayerData = [...allPlayerData, ...batchData];
      } else {
        console.error(`Failed to fetch data for batch: ${batch}`);
      }
    }

    const processedData = allPlayerData.map(player => {
      let stats = {};
      let totalGames = 0;

      if (month === 'all') {
        stats = player.game_stats?.[`y${year}`]?.player_total || {};
        totalGames = player.game_stats?.[`y${year}`]?.total_games || 0;
      } else {
        stats = player.game_stats?.[`y${year}`]?.[`m${month}`]?.player_total || {};
        totalGames = player.game_stats?.[`y${year}`]?.[`m${month}`]?.total_games || 0;
      }

      return {
        ...player,
        stats,
        totalGames
      };
    });

    setLeaderboardData(processedData);
    setIsLoading(false);
  }, [fetchPlayersList, fetchPlayersBatch]);

  return { leaderboardData, isLoading, updateLeaderboard };
}

export default useApi;