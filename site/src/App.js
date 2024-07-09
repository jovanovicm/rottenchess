import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FilterBar from './components/FilterBar';
import Leaderboard from './components/Leaderboard';
import useLeaderboard from './utils/api';  // Update path

function App() {
  const [currentFilter, setCurrentFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear().toString());
  const [currentMonth, setCurrentMonth] = useState((new Date().getMonth() + 1).toString().padStart(2, '0'));
  const [sortColumn, setSortColumn] = useState(3);  // Default to RpG
  const [sortDirection, setSortDirection] = useState('desc');  // Default to descending

  const { leaderboardData, isLoading, updateLeaderboard } = useLeaderboard();

  useEffect(() => {
    updateLeaderboard(currentYear, currentMonth);
  }, [currentYear, currentMonth]);

  useEffect(() => {
    if (currentFilter === 'top50') {
      setSortColumn(0);
      setSortDirection('asc');
    } else {
      setSortColumn(3);
      setSortDirection('desc');
    }
  }, [currentFilter]);

  return (
    <div className="App">
      <Header />
      <FilterBar 
        currentFilter={currentFilter}
        setCurrentFilter={setCurrentFilter}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        currentYear={currentYear}
        setCurrentYear={setCurrentYear}
        currentMonth={currentMonth}
        setCurrentMonth={setCurrentMonth}
        setSortColumn={setSortColumn}
        setSortDirection={setSortDirection}
      />
      <Leaderboard 
        data={leaderboardData}
        isLoading={isLoading}
        currentFilter={currentFilter}
        searchTerm={searchTerm}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        setSortColumn={setSortColumn}
        setSortDirection={setSortDirection}
      />
    </div>
  );
}

export default App;