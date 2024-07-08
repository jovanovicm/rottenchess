import React, { useState, useEffect } from 'react';

const FilterBar = ({ onFilterChange, currentYear, currentMonth }) => {
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);

  useEffect(() => {
    onFilterChange('all', year, month);
  }, [year, month]);

  return (
    <div className="filter-bar">
      <div className="left-filters">
        <button className="pill" onClick={() => onFilterChange('all', year, month)}>All</button>
        <button className="pill" onClick={() => onFilterChange('top50', year, month)}>Top 50 Blitz</button>
        <button className="pill" onClick={() => onFilterChange('personality', year, month)}>Chess Personalities</button>
        <input type="text" className="pill search-box" onInput={(e) => onFilterChange(e.target.value, year, month)} placeholder="Search Player..." />
      </div>
      <div className="right-filters">
        <select id="year-selector" value={year} onChange={(e) => setYear(e.target.value)}>
          {Array.from({ length: new Date().getFullYear() - 2024 + 1 }, (_, i) => 2024 + i).map(year => (
            <option key={year} value={year}>{year}</option>
          ))}
        </select>
        <select id="month-selector" value={month} onChange={(e) => setMonth(e.target.value)}>
          <option value="all">All Months</option>
          {Array.from({ length: 12 }, (_, i) => (i + 1).toString().padStart(2, "0")).map(month => (
            <option key={month} value={month}>{new Date(2000, month - 1, 1).toLocaleString("default", { month: "long" })}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default FilterBar;