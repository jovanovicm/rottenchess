function filterLeaderboard(category) {
    const rows = document.querySelectorAll('#leaderboard-body tr');
    const pills = document.querySelectorAll('.pill');
    let activePill = document.querySelector('.pill.active');

    if (activePill && activePill.getAttribute('onclick').includes(category)) {
        if (category !== 'all') {
            // Deselect current pill, show all results
            activePill.classList.remove('active');
            category = 'all';
            pills[0].classList.add('active'); // Assuming the first pill is "All"
        }
    } else {
        // Update active pill visually
        pills.forEach(pill => {
            if (pill.getAttribute('onclick').includes(category)) {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });
    }

    // Show or hide rows based on category
    rows.forEach(row => {
        if (row.dataset.category === category || category === 'all') {
            row.style.display = ''; // Show row
        } else {
            row.style.display = 'none'; // Hide row
        }
    });
}

function sortTable(columnIndex, thElement) {
    const table = document.getElementById("leaderboard-body");
    let rows = Array.from(table.rows);
    const isAscending = thElement.classList.contains('asc');

    // Remove ascending/descending classes from all headers
    document.querySelectorAll('.leaderboard th').forEach(th => {
        th.classList.remove('asc', 'desc');
    });

    // Toggle sort direction and update the class on the clicked header
    if (isAscending) {
        thElement.classList.add('desc');  // If it was ascending, now make it descending
        thElement.classList.remove('asc');
    } else {
        thElement.classList.add('asc');   // If it was descending or neutral, now make it ascending
        thElement.classList.remove('desc');
    }

    // Sort rows based on the new direction
    rows.sort((rowA, rowB) => {
        const cellA = rowA.cells[columnIndex].textContent.trim();
        const cellB = rowB.cells[columnIndex].textContent.trim();

        // Adjust this logic if sorting more complex data like numbers or dates
        if (isAscending) {
            return cellB.localeCompare(cellA, undefined, {numeric: true});  // For descending order
        } else {
            return cellA.localeCompare(cellB, undefined, {numeric: true});  // For ascending order
        }
    });

    // Reattach rows in new order
    rows.forEach(row => table.appendChild(row));
}

