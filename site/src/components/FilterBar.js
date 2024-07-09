import React from 'react';

function FilterBar({ currentFilter, setCurrentFilter, searchTerm, setSearchTerm, currentYear, setCurrentYear, currentMonth, setCurrentMonth, setSortColumn, setSortDirection }) {
  const handleFilterClick = (filter) => {
    setCurrentFilter(filter);
    if (filter === 'top50') {
      setSortColumn(0);
      setSortDirection('asc');
    } else {
      setSortColumn(3);
      setSortDirection('desc');
    }
  };

  return (
    <div className="filter-bar">
      <div className="left-filters">
        <button className={`pill ${currentFilter === 'all' ? 'active' : ''}`} onClick={() => handleFilterClick('all')} id="all">All</button>
        <button className={`pill ${currentFilter === 'top50' ? 'active' : ''}`} onClick={() => handleFilterClick('top50')}>Top 50 Blitz</button>
        <button className={`pill ${currentFilter === 'personality' ? 'active' : ''}`} onClick={() => handleFilterClick('personality')}>Chess Personalities</button>
        <input 
          type="text" 
          className="pill search-box" 
          placeholder="Search Player..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>
      <div className="right-filters">
        <select value={currentYear} onChange={(e) => setCurrentYear(e.target.value)}>
          {Array.from({ length: new Date().getFullYear() - 2023 }, (_, i) => 2024 + i).map(year => (
            <option key={year} value={year}>{year}</option>
          ))}
        </select>
        <select value={currentMonth} onChange={(e) => setCurrentMonth(e.target.value)}>
          <option value="all">All Months</option>
          {Array.from({ length: 12 }, (_, i) => {
            const month = (i + 1).toString().padStart(2, '0');
            return (
              <option key={month} value={month}>
                {new Date(2000, i, 1).toLocaleString('default', { month: 'long' })}
              </option>
            );
          })}
        </select>
      </div>
    </div>
  );
}

export default FilterBar;