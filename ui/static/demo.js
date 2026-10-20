(() => {
    const button = document.getElementById("run-demo");
    const output = document.getElementById("demo-output");
    const summary = document.getElementById("demo-summary");
    const tbody = document.querySelector("#demo-table tbody");
    const status = document.getElementById("demo-status");

    if (!button || !output || !summary || !tbody || !status) {
        return;
    }

    const setStatus = (message, tone) => {
        status.textContent = message;
        status.style.color = tone === "error" ? "var(--danger)" : "var(--faint)";
    };

    const textCell = (text, className) => {
        const cell = document.createElement("td");
        if (className) {
            cell.className = className;
        }
        cell.textContent = text;
        return cell;
    };

    const chipCell = (text, className) => {
        const cell = document.createElement("td");
        const chip = document.createElement("span");
        chip.className = "chip " + className;
        chip.textContent = text;
        cell.append(chip);
        return cell;
    };

    const render = (data) => {
        tbody.replaceChildren();
        const results = Array.isArray(data.results) ? data.results : [];
        results.forEach((result) => {
            const row = document.createElement("tr");
            row.append(
                textCell(result.name || "-"),
                chipCell(result.expected || "-", result.expected === "allow" ? "chip-ok" : "chip-block"),
                chipCell(result.actual || "error", result.actual === "allow" ? "chip-ok" : "chip-block"),
                textCell(result.source || "-"),
                chipCell(result.ok ? "ok" : "FAIL", result.ok ? "chip-ok" : "chip-block"),
                textCell(result.reason || "-", "cell-reason")
            );
            tbody.append(row);
        });

        const passed = Number(data.passed) || 0;
        const total = Number(data.total) || results.length;
        const delta = data.audit_delta;
        const passedAll = passed === total && total > 0;

        summary.replaceChildren();
        const verdict = document.createElement("span");
        verdict.className = "chip " + (passedAll ? "chip-ok" : "chip-block");
        verdict.textContent = passedAll ? "PASS" : "FAIL";
        const detail = document.createElement("span");
        detail.className = "muted";
        detail.textContent =
            passed + "/" + total + " cases" +
            (typeof delta === "number" ? " · audit +" + delta : "");
        summary.append(verdict, detail);
        output.hidden = false;
    };

    const run = async () => {
        button.disabled = true;
        setStatus("Running the five cases...", "info");
        try {
            const response = await fetch("/demo/run", {
                method: "POST",
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: "{}",
            });
            const data = await response.json().catch(() => null);
            if (!response.ok) {
                setStatus((data && data.error) || "The demo could not run.", "error");
                return;
            }
            render(data);
            setStatus("Validation only. Nothing was executed.", "info");
        } catch (error) {
            setStatus("Guardian is unreachable. Check the stack.", "error");
        } finally {
            button.disabled = false;
        }
    };

    button.addEventListener("click", run);
    if (new URLSearchParams(location.search).get("autorun") === "1") {
        run();
    }
})();
