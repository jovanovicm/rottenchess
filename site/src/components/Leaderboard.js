import React, { useMemo, useEffect, useState } from 'react';
import LeaderboardRow from './LeaderboardRow';

function calculateRPG(stats, totalGames) {
  if (!totalGames || totalGames === 0) return 0;
  return (
    (((stats.blunders || 0) * 3) +
      ((stats.mistakes || 0) * 2) +
      (stats.inaccuracies || 0)) /
    totalGames
  );
}

function sortData(data, column, direction) {
  return [...data].sort((a, b) => {
    let valueA, valueB;

    switch (column) {
      case 0: // Ranking
        valueA = (a.historicalRank !== undefined ? a.historicalRank : a.player_rank) || Infinity;
        valueB = (b.historicalRank !== undefined ? b.historicalRank : b.player_rank) || Infinity;
        break;
      case 1: // Username
        valueA = a.username.toLowerCase();
        valueB = b.username.toLowerCase();
        return direction === 'asc' ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA);
      case 2: // Rating
        valueA = a.historicalRating !== undefined ? a.historicalRating : a.rating;
        valueB = b.historicalRating !== undefined ? b.historicalRating : b.rating;
        break;
      case 3: // RpG
        valueA = calculateRPG(a.stats, a.totalGames);
        valueB = calculateRPG(b.stats, b.totalGames);
        break;
      case 4: // Games played
        valueA = a.totalGames;
        valueB = b.totalGames;
        break;
      case 5: // Blunders
        valueA = a.stats.blunders || 0;
        valueB = b.stats.blunders || 0;
        break;
      case 6: // Mistakes
        valueA = a.stats.mistakes || 0;
        valueB = b.stats.mistakes || 0;
        break;
      case 7: // Inaccuracies
        valueA = a.stats.inaccuracies || 0;
        valueB = b.stats.inaccuracies || 0;
        break;
      default:
        return 0;
    }

    if (valueA < valueB) return direction === 'asc' ? -1 : 1;
    if (valueA > valueB) return direction === 'asc' ? 1 : -1;
    return 0;
  });
}

function Leaderboard({
  data,
  isLoading,
  currentFilter,
  searchTerm,
  sortColumn,
  sortDirection,
  setSortColumn,
  setSortDirection,
}) {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 968);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 968);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSort = (columnIndex) => {
    if (columnIndex === sortColumn) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedData = useMemo(() => {
    let filtered = data.filter((player) => {
      const matchesFilter =
        currentFilter === 'all' ||
        (currentFilter === 'top50' && player.is_leaderboard_player) ||
        (currentFilter === 'personality' && player.is_personality_player);
      const searchableText = `${player.username} ${player.player_name || ''}`.toLowerCase();
      const matchesSearch = searchableText.includes(searchTerm.toLowerCase());
      return matchesFilter && matchesSearch;
    });
    return sortData(filtered, sortColumn, sortDirection);
  }, [data, currentFilter, searchTerm, sortColumn, sortDirection]);

  useEffect(() => {
    if (currentFilter === 'top50') {
      setSortColumn(0); // Ranking
      setSortDirection('asc'); // Ascending
    } else {
      setSortColumn(3); // RpG
      setSortDirection('desc'); // Descending
    }
  }, [currentFilter, setSortColumn, setSortDirection]);

  if (isLoading) {
    return (
      <div className="loader">
        {/* Loader SVG or any loading indicator */}
        <svg
          version="1.1"
          id="loader-1"
          xmlns="http://www.w3.org/2000/svg"
          x="0px"
          y="0px"
          width="40px"
          height="40px"
          viewBox="0 0 50 50"
          style={{ enableBackground: 'new 0 0 50 50' }}
          xmlSpace="preserve"
        >
          <path
            fill="#000"
            d="M43.935,25.145c0-10.318-8.364-18.683-18.683-18.683c-10.318,0-18.683,8.365-18.683,18.683h4.068
              c0-8.071,6.543-14.615,14.615-14.615c8.072,0,14.615,6.543,14.615,14.615H43.935z"
          >
            <animateTransform
              attributeType="xml"
              attributeName="transform"
              type="rotate"
              from="0 25 25"
              to="360 25 25"
              dur="0.75s"
              repeatCount="indefinite"
            />
          </path>
        </svg>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="leaderboard">
        <thead>
          <tr>
            {currentFilter === 'top50' && (
              <th onClick={() => handleSort(0)}>
                <div className="th-content">
                  <span className="full-text">Ranking</span>
                  <span className="short-text">Rk.</span>
                  <div className="sort-arrows">
                    <img
                      src="/icons/arrow-up.png"
                      className={`sort-arrow ${
                        sortColumn === 0 && sortDirection === 'asc' ? 'active' : ''
                      }`}
                      alt="Sort ascending"
                    />
                    <img
                      src="/icons/arrow-down.png"
                      className={`sort-arrow ${
                        sortColumn === 0 && sortDirection === 'desc' ? 'active' : ''
                      }`}
                      alt="Sort descending"
                    />
                  </div>
                </div>
              </th>
            )}
            <th onClick={() => handleSort(1)}>
              <div className="th-content">
                Username
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 1 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 1 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(2)} className="rating-column">
              <div className="th-content">
                Rating
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 2 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 2 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(3)}>
              <div className="th-content">
                RpG
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 3 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 3 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(4)}>
              <div className="th-content">
                <span className="full-text">Games played</span>
                <span className="short-text">Gp</span>
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 4 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 4 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(5)}>
              <div className="th-content">
                <span className="text-with-icon">
                  Blunders
                  <span className="icon-wrapper">
                    <img src="/icons/blunder.png" className="icon" alt="Blunder icon" />
                  </span>
                </span>
                <span className="icon-only">
                  <span className="icon-wrapper">
                    <img src="/icons/blunder.png" className="icon" alt="Blunder icon" />
                  </span>
                </span>
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 5 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 5 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(6)}>
              <div className="th-content">
                <span className="text-with-icon">
                  Mistakes
                  <span className="icon-wrapper">
                    <img src="/icons/mistake.png" className="icon" alt="Mistake icon" />
                  </span>
                </span>
                <span className="icon-only">
                  <span className="icon-wrapper">
                    <img src="/icons/mistake.png" className="icon" alt="Mistake icon" />
                  </span>
                </span>
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 6 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 6 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
            <th onClick={() => handleSort(7)}>
              <div className="th-content">
                <span className="text-with-icon">
                  Inaccuracies
                  <span className="icon-wrapper">
                    <img
                      src="/icons/inaccuracy.png"
                      className="icon"
                      alt="Inaccuracy icon"
                    />
                  </span>
                </span>
                <span className="icon-only">
                  <span className="icon-wrapper">
                    <img
                      src="/icons/inaccuracy.png"
                      className="icon"
                      alt="Inaccuracy icon"
                    />
                  </span>
                </span>
                <div className="sort-arrows">
                  <img
                    src="/icons/arrow-up.png"
                    className={`sort-arrow ${
                      sortColumn === 7 && sortDirection === 'asc' ? 'active' : ''
                    }`}
                    alt="Sort ascending"
                  />
                  <img
                    src="/icons/arrow-down.png"
                    className={`sort-arrow ${
                      sortColumn === 7 && sortDirection === 'desc' ? 'active' : ''
                    }`}
                    alt="Sort descending"
                  />
                </div>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {filteredAndSortedData.map((player) => (
            <LeaderboardRow key={player.username} player={player} currentFilter={currentFilter} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Leaderboard;