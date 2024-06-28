// Global variables
let currentFilter = 'all';
let currentYear = new Date().getFullYear().toString();
let currentMonth = (new Date().getMonth() + 1).toString().padStart(2, '0');

document.addEventListener("DOMContentLoaded", function() {
    const allPill = document.getElementById('all');
    allPill.classList.add('active');
    filterLeaderboard('all', allPill);

    const rankingColumn = document.querySelector('.ranking-column');
    rankingColumn.setAttribute('data-sort-direction', 'asc');
    sortTable(0, rankingColumn, true);

    setupYearMonthSelectors();
    updateLeaderboard();
});

function setupYearMonthSelectors() {
    const yearSelector = document.getElementById('year-selector');
    const monthSelector = document.getElementById('month-selector');

    // Populate year selector (assuming data from 2024 onwards)
    const currentYear = new Date().getFullYear();
    for (let year = 2024; year <= currentYear; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelector.appendChild(option);
    }
    yearSelector.value = currentYear;

    // Populate month selector
    for (let month = 1; month <= 12; month++) {
        const option = document.createElement('option');
        option.value = month.toString().padStart(2, '0');
        option.textContent = new Date(2000, month - 1, 1).toLocaleString('default', { month: 'long' });
        monthSelector.appendChild(option);
    }
    monthSelector.value = currentMonth;

    yearSelector.addEventListener('change', function() {
        currentYear = this.value;
        updateLeaderboard();
    });

    monthSelector.addEventListener('change', function() {
        currentMonth = this.value;
        updateLeaderboard();
    });
}

async function fetchPlayersList() {
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
}

async function fetchPlayersBatch(usernames) {
    try {
        const response = await fetch('https://api.rottenchess.com/players/stats?batch=true', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ usernames })
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching players batch:', error);
        return null;
    }
}

function showLoading() {
    const leaderboardBody = document.getElementById('leaderboard-body');
    leaderboardBody.innerHTML = '<tr><td colspan="7">Loading...</td></tr>';
}

function hideLoading() {
    const loadingRow = document.querySelector('#leaderboard-body tr');
    if (loadingRow && loadingRow.textContent.includes('Loading...')) {
        loadingRow.remove();
    }
}

async function updateLeaderboard() {
    showLoading();

    const playersList = await fetchPlayersList();
    if (!playersList) {
        console.error('Failed to fetch players list');
        hideLoading();
        return;
    }

    const allPlayers = [
        ...playersList.leaderboard_players.active,
        ...playersList.personality_players
    ];

    const batches = chunkArray(allPlayers, 50);
    const leaderboardBody = document.getElementById('leaderboard-body');
    leaderboardBody.innerHTML = '';

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
    applyFilters();
    const rankingColumn = document.querySelector('.ranking-column');
    sortTable(0, rankingColumn, true);
}

function chunkArray(array, size) {
    const result = [];
    for (let i = 0; i < array.length; i += size) {
        result.push(array.slice(i, i + size));
    }
    return result;
}

function createPlayerRow(playerData) {
    const row = document.createElement('tr');
    row.setAttribute('data-category', playerData.is_leaderboard_player ? 'top50' : 'personality');

    const { stats, totalGames } = getPlayerStats(playerData);
    const rmg = calculateRMG(stats, totalGames);

    row.innerHTML = `
        <td>${playerData.player_rank}</td>
        <td><div class="leaderboard-chess-title">${playerData.player_title}</div> ${playerData.player_name}</td>
        <td>${playerData.rating}</td>
        <td>${stats.blunders || 0}</td>
        <td>${stats.mistakes || 0}</td>
        <td>${stats.inaccuracies || 0}</td>
        <td>${rmg.toFixed(2)}</td>
    `;

    return row;
}

function getPlayerStats(playerData) {
    let stats = {};
    let totalGames = 0;

    if (currentMonth === 'all') {
        stats = playerData.game_stats?.[`y${currentYear}`]?.player_total || {};
        totalGames = playerData.game_stats?.[`y${currentYear}`]?.total_games || 0;
    } else {
        stats = playerData.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]?.player_total || {};
        totalGames = playerData.game_stats?.[`y${currentYear}`]?.[`m${currentMonth}`]?.total_games || 0;
    }

    return { stats, totalGames };
}

function calculateRMG(stats, totalGames) {
    if (!totalGames || totalGames === 0) return 0;
    return ((stats.blunders || 0) + (stats.mistakes || 0) + (stats.inaccuracies || 0)) / totalGames;
}

function filterLeaderboard(category, element) {
    const pills = document.querySelectorAll('.pill');
    const isActive = element.classList.contains('active');

    pills.forEach(pill => pill.classList.remove('active'));

    if (isActive && category !== 'all') {
        document.getElementById('all').classList.add('active');
        currentFilter = 'all';
    } else {
        element.classList.add('active');
        currentFilter = category;
    }

    applyFilters();
}

function applyFilters() {
    const searchText = document.querySelector('.search-box').value.toLowerCase();
    const rows = document.querySelectorAll('#leaderboard-body tr');
    rows.forEach(row => {
        const usernameCell = row.getElementsByTagName("TD")[1];
        const username = usernameCell.textContent || usernameCell.innerText;

        if (username.toLowerCase().indexOf(searchText) > -1 && (currentFilter === 'all' || row.getAttribute('data-category') === currentFilter)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
}

function filterByName() {
    applyFilters();
}

function sortTable(columnIndex, headerElement, initial = false) {
    let table = document.getElementById("leaderboard-body");
    let rows = Array.from(table.rows);
    let direction = headerElement.getAttribute('data-sort-direction');
    const isRankingColumn = columnIndex === 0;

    if (initial) {
        rows.sort((a, b) => {
            let valA = parseFloat(a.cells[columnIndex].textContent.trim());
            let valB = parseFloat(b.cells[columnIndex].textContent.trim());
            return valA - valB;
        });
    } else {
        if (isRankingColumn) {
            direction = direction === 'asc' ? 'desc' : 'asc';
        } else {
            if (!direction || direction === 'default') {
                direction = 'desc';
            } else if (direction === 'desc') {
                direction = 'asc';
            } else if (direction === 'asc') {
                direction = 'default';
            }
        }

        headerElement.setAttribute('data-sort-direction', direction);

        if (direction !== 'default') {
            rows.sort((a, b) => {
                let valA = parseFloat(a.cells[columnIndex].textContent.trim());
                let valB = parseFloat(b.cells[columnIndex].textContent.trim());
                return (direction === 'asc' ? valA - valB : valB - valA);
            });
        } else {
            rows.sort((a, b) => {
                let rankA = parseFloat(a.cells[0].textContent.trim());
                let rankB = parseFloat(b.cells[0].textContent.trim());
                return rankA - rankB;
            });
            headerElement.removeAttribute('data-sort-direction');
        }
    }

    rows.forEach(row => table.appendChild(row));
}
