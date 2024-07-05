// Global variables
let currentFilter = "all";
let currentYear = new Date().getFullYear().toString();
let currentMonth = (new Date().getMonth() + 1).toString().padStart(2, "0");

document.addEventListener("DOMContentLoaded", function () {
  const allPill = document.getElementById("all");
  filterLeaderboard("all", allPill);
  setupYearMonthSelectors();
  updateLeaderboard();
});

function setupYearMonthSelectors() {
  const yearSelector = document.getElementById("year-selector");
  const monthSelector = document.getElementById("month-selector");

  // Populate year selector (assuming data from 2024 onwards)
  const currentYear = new Date().getFullYear();
  for (let year = 2024; year <= currentYear; year++) {
    const option = document.createElement("option");
    option.value = year;
    option.textContent = year;
    yearSelector.appendChild(option);
  }
  yearSelector.value = currentYear;

  // Populate month selector
  for (let month = 1; month <= 12; month++) {
    const option = document.createElement("option");
    option.value = month.toString().padStart(2, "0");
    option.textContent = new Date(2000, month - 1, 1).toLocaleString(
      "default",
      { month: "long" }
    );
    monthSelector.appendChild(option);
  }
  monthSelector.value = currentMonth;

  yearSelector.addEventListener("change", function () {
    currentYear = this.value;
    updateLeaderboard();
  });

  monthSelector.addEventListener("change", function () {
    currentMonth = this.value;
    updateLeaderboard();
  });
}

async function fetchPlayersList() {
  try {
    const response = await fetch("https://api.rottenchess.com/players");
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching players list:", error);
    return null;
  }
}

async function fetchPlayersBatch(usernames) {
  try {
    const response = await fetch("https://api.rottenchess.com/players/batch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ usernames }),
    });
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching players batch:", error);
    return null;
  }
}

function showLoading() {
  const leaderboardBody = document.getElementById("leaderboard-body");
  leaderboardBody.innerHTML = `
  <tr id="loading-container">
    <td colspan="7">
        <div class="loader loader--style3" title="2">
            <svg version="1.1" id="loader-1" xmlns="http://www.w3.org/2000/svg"
                xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
                width="40px" height="40px" viewBox="0 0 50 50" style="enable-background:new 0 0 50 50;"
                xml:space="preserve">
                <path fill="#000" d="M43.935,25.145c0-10.318-8.364-18.683-18.683-18.683c-10.318,0-18.683,8.365-18.683,18.683h4.068c0-8.071,6.543-14.615,14.615-14.615c8.072,0,14.615,6.543,14.615,14.615H43.935z">
                    <animateTransform attributeType="xml"
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
    </td>
  </tr>`;
}

function hideLoading() {
  const loadingRow = document.getElementById("loading-container");
  if (loadingRow) {
    loadingRow.remove();
  }
}

async function updateLeaderboard() {
  showLoading();

  const playersList = await fetchPlayersList();
  if (!playersList) {
    console.error("Failed to fetch players list");
    hideLoading();
    return;
  }

  const allPlayers = [
    ...playersList.leaderboard_players.active,
    ...playersList.personality_players,
  ];

  const batches = chunkArray(allPlayers, 50);
  const leaderboardBody = document.getElementById("leaderboard-body");
  leaderboardBody.innerHTML = "";

  for (const batch of batches) {
    const batchData = await fetchPlayersBatch(batch);
    if (batchData) {
      for (const playerData of batchData) {
        const row = createPlayerRow(playerData);
        leaderboardBody.appendChild(row);
      }
    } else {
      console.error(`Failed to fetch data for batch: ${batch}`);
    }
  }

  hideLoading();
  highlightPlayers();
  applyFilters();
  sortTableByCurrentFilter();
}

function chunkArray(array, size) {
  const result = [];
  for (let i = 0; i < array.length; i += size) {
    result.push(array.slice(i, i + size));
  }
  return result;
}

function createPlayerRow(playerData) {
  const row = document.createElement("tr");
  row.setAttribute(
      "data-category",
      playerData.is_leaderboard_player ? "top50" : "personality"
  );

  const { stats, totalGames } = getPlayerStats(playerData);
  const rpg = calculateRPG(stats, totalGames);

  const buttons = Array.from(document.getElementsByClassName("pill"));
  let currentFilter = null;
  buttons.forEach((button) => {
      if (button.classList.contains("active")) {
          currentFilter = button.innerHTML;
      }
  });

  const style = currentFilter === "Top 50 Blitz" ? "" : `"display: none;"`;

  const title = playerData.player_title !== "None" ? `<div class="leaderboard-chess-title">${playerData.player_title}</div>` : "";

  const playerURL = `https://www.chess.com/member/${playerData.username}`;
  
  // Dynamically construct the country flag class
  const countryCodeClass = getCountryCodeClass(playerData.country);

  row.innerHTML = `
      <td style=${style}>${playerData.player_rank}</td>
      <td>${title} <a href="${playerURL}" target="_blank">${playerData.player_name}</a> <div class="country-flag ${countryCodeClass}"></div></td>
      <td>${playerData.rating}</td>
      <td><strong>${rpg.toFixed(2)}</strong></td>
      <td>${totalGames || 0}</td>
      <td>${stats.blunders || 0}</td>
      <td>${stats.mistakes || 0}</td>
      <td>${stats.inaccuracies || 0}</td>
  `;

  return row;
}

function getCountryCodeClass(country) {
  return `country-${country.toLowerCase()}`;
}

function getPlayerStats(playerData) {
  let stats = {};
  let totalGames = 0;

  if (currentMonth === "all") {
    stats = playerData.game_stats?.[`y${currentYear}`]?.player_total || {};
    totalGames = playerData.game_stats?.[`y${currentYear}`]?.total_games || 0;
  } else {
    stats =
      playerData.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]
        ?.player_total || {};
    totalGames =
      playerData.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]
        ?.total_games || 0;
  }

  return { stats, totalGames };
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

function filterLeaderboard(category, element) {
  const pills = document.querySelectorAll(".pill");
  pills.forEach((pill) => pill.classList.remove("active"));
  element.classList.add("active");
  currentFilter = category;

  const rankingColumn = document.querySelector(".ranking-column");
  const rankingCells = document.querySelectorAll("td:first-child");

  if (category === "top50") {
    rankingColumn.style.display = "";
    rankingCells.forEach((cell) => (cell.style.display = ""));
  } else {
    rankingColumn.style.display = "none";
    rankingCells.forEach((cell) => (cell.style.display = "none"));
  }

  applyFilters();
  sortTableByCurrentFilter();
}

function applyFilters() {
  const searchText = document.querySelector(".search-box").value.toLowerCase();
  const rows = document.querySelectorAll("#leaderboard-body tr");
  rows.forEach((row) => {
    const usernameCell = row.getElementsByTagName("TD")[1];
    const username = usernameCell.textContent || usernameCell.innerText;
    const category = row.getAttribute("data-category");

    const matchesSearch = username.toLowerCase().indexOf(searchText) > -1;
    const matchesFilter = currentFilter === "all" || category === currentFilter;

    row.style.display = matchesSearch && matchesFilter ? "" : "none";
  });
}

function filterByName() {
  applyFilters();
}

async function sortTableByCurrentFilter() {
  const table = document.querySelector(".leaderboard");
  const headers = table.querySelectorAll("th");

  if (currentFilter === "top50") {
    // Fires on button click
    // Therefore, do not toggle ascending/descending
    sortTable(0, headers[0], false); // Sort by ranking
  } else {
    sortTable(3, headers[3], false); // Sort by RP/G
  }
}

function sortTable(columnIndex, headerElement, toggle = true) {
  let table = document.getElementById("leaderboard-body");
  let rows = Array.from(table.rows);
  let direction = headerElement.getAttribute("data-sort-direction");

  if (toggle) {
    direction = direction === "asc" ? "desc" : "asc";
    headerElement.setAttribute("data-sort-direction", direction);
  }

  rows.sort((a, b) => {
    let cellA = a.cells[columnIndex].textContent.trim();
    let cellB = b.cells[columnIndex].textContent.trim();

    // Special handling for the ranking column
    if (columnIndex === 0) {
      let rankA = a.getAttribute("data-category") === "top50" ? parseInt(cellA) || Infinity : Infinity;
      let rankB = b.getAttribute("data-category") === "top50" ? parseInt(cellB) || Infinity : Infinity;
      return direction === "asc" ? rankA - rankB : rankB - rankA;
    }

    // For other columns, use numeric sorting
    let valueA = parseFloat(cellA) || 0;
    let valueB = parseFloat(cellB) || 0;
    return direction === "asc" ? valueA - valueB : valueB - valueA;
  });

  // Reorder the rows without removing any
  rows.forEach(row => table.appendChild(row));

  // Update sort arrow visibility
  const arrows = headerElement.querySelectorAll(".sort-arrow");
  arrows.forEach(arrow => arrow.classList.remove("active"));
  headerElement.querySelector(direction === "asc" ? ".up-arrow" : ".down-arrow").classList.add("active");

  // Apply current filter after sorting
  applyFilters();
}

function highlightPlayers() {
  const rows = document.querySelectorAll("#leaderboard-body tr");
  rows.forEach((row) => {
    if (row.getAttribute("data-category") === "personality") {
      row.style.backgroundColor = "#EDEDF5"; 
    }
  });
}
