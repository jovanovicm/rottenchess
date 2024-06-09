// Global variable to keep track of current filter
let currentFilter = 'all';

document.addEventListener("DOMContentLoaded", function() {
    const allPill = document.getElementById('all');
    allPill.classList.add('active');
    filterLeaderboard('all', allPill);

    const rankingColumn = document.querySelector('.ranking-column');
    // Initialize the sort direction to 'asc' for the ranking column on page load
    rankingColumn.setAttribute('data-sort-direction', 'asc');
    sortTable(0, rankingColumn, true); // Default sort by Ranking in ascending order
});

function filterLeaderboard(category, element) {
    const pills = document.querySelectorAll('.pill');
    const isActive = element.classList.contains('active');

    // Remove active class from all pills
    pills.forEach(pill => pill.classList.remove('active'));

    if (isActive && category !== 'all') {
        // If the clicked pill is already active and not the 'all' category, reset to 'all'
        document.getElementById('all').classList.add('active');
        currentFilter = 'all';
    } else {
        // Otherwise, activate the clicked pill and set the current filter
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
    applyFilters();  // This function is called on input events from the search box
}

function sortTable(columnIndex, headerElement, initial = false) {
    let table = document.getElementById("leaderboard-body");
    let rows = Array.from(table.rows);
    let direction = headerElement.getAttribute('data-sort-direction');
    const isRankingColumn = columnIndex === 0; // Assuming the ranking column is the first column

    if (initial) {
        // Perform initial sorting without toggling direction
        rows.sort((a, b) => {
            let valA = parseFloat(a.cells[columnIndex].textContent.trim());
            let valB = parseFloat(b.cells[columnIndex].textContent.trim());
            return valA - valB; // Always ascending for initial sort
        });
    } else {
        // Normal sorting behavior, toggling between states
        if (isRankingColumn) {
            // For ranking column, toggle only between asc and desc
            if (!direction || direction === 'asc') {
                direction = 'desc';
            } else {
                direction = 'asc';
            }
        } else {
            // For other columns, toggle between desc, asc, and default
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
            // Sort rows based on the current direction
            rows.sort((a, b) => {
                let valA = parseFloat(a.cells[columnIndex].textContent.trim());
                let valB = parseFloat(b.cells[columnIndex].textContent.trim());
                return (direction === 'asc' ? valA - valB : valB - valA);
            });
        } else {
            // Default sorting: Sort by the ranking column, ascending
            rows.sort((a, b) => {
                let rankA = parseFloat(a.cells[0].textContent.trim());
                let rankB = parseFloat(b.cells[0].textContent.trim());
                return rankA - rankB;
            });
            headerElement.removeAttribute('data-sort-direction'); // Remove attribute when back to default
        }
    }

    // Re-append sorted rows back to the table
    rows.forEach(row => table.appendChild(row));
}