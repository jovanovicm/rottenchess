import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FilterBar from './components/FilterBar';
import Leaderboard from './components/Leaderboard';
import { fetchPlayersList, fetchPlayersBatch } from './api';

function App() {
  const [currentFilter, setCurrentFilter] = useState('all');
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear().toString());
  const [currentMonth, setCurrentMonth] = useState((new Date().getMonth() + 1).toString().padStart(2, "0"));
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  const updateLeaderboard = async () => {
    setLoading(true);

    const playersList = await fetchPlayersList();
    if (!playersList) {
      console.error("Failed to fetch players list");
      setLoading(false);
      return;
    }

    const allPlayers = [
      ...playersList.leaderboard_players.active,
      ...playersList.personality_players,
    ];

    const batches = chunkArray(allPlayers, 50);
    const allBatchData = [];

    for (const batch of batches) {
      const batchData = await fetchPlayersBatch(batch);
      if (batchData) {
        allBatchData.push(...batchData);
      } else {
        console.error(`Failed to fetch data for batch: ${batch}`);
      }
    }

    setPlayers(allBatchData);
    setLoading(false);
  };

  useEffect(() => {
    updateLeaderboard();
  }, [currentFilter, currentYear, currentMonth]);

  const chunkArray = (array, size) => {
    const result = [];
    for (let i = 0; i < array.length; i += size) {
      result.push(array.slice(i, i + size));
    }
    return result;
  };

  const onFilterChange = (filter, year, month) => {
    setCurrentFilter(filter);
    setCurrentYear(year);
    setCurrentMonth(month);
  };

  return (
    <div>
      <Header />
      <FilterBar onFilterChange={onFilterChange} currentYear={currentYear} currentMonth={currentMonth} />
      <Leaderboard players={players} filter={currentFilter} loading={loading} />
    </div>
  );
}

export default App;