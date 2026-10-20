(() => {
    const search = document.getElementById("decision-search");
    const status = document.getElementById("decision-status");
    const table = document.getElementById("decision-table");
    const empty = document.getElementById("empty-filter");

    if (!search || !status || !table || !empty) {
        return;
    }

    const rows = Array.from(table.querySelectorAll("tbody tr"));

    const applyFilters = () => {
        const query = search.value.trim().toLowerCase();
        const wanted = status.value;
        let visible = 0;

        rows.forEach((row) => {
            const haystack = row.dataset.search || "";
            const matchesText = !query || haystack.includes(query);
            const matchesStatus = !wanted || row.dataset.status === wanted;
            const show = matchesText && matchesStatus;
            row.hidden = !show;
            if (show) {
                visible += 1;
            }
        });

        empty.hidden = visible !== 0;
    };

    search.addEventListener("input", applyFilters);
    status.addEventListener("change", applyFilters);
})();
