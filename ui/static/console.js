(() => {
  const scenarios = JSON.parse(document.getElementById("console-scenarios").textContent || "[]");
  const params = new URLSearchParams(window.location.search);
  const form = document.getElementById("console-form");
  const taskInput = document.getElementById("console-task");
  const commandInput = document.getElementById("console-command");
  const untrustedInput = document.getElementById("console-untrusted");
  const status = document.getElementById("console-status");
  const submit = document.getElementById("console-submit");
  const traceState = document.getElementById("trace-state");
  const badge = document.getElementById("decision-badge");
  const reason = document.getElementById("decision-reason");
  const title = document.getElementById("decision-title");
  const source = document.getElementById("decision-source");
  const validationId = document.getElementById("decision-id");
  const observerBody = document.getElementById("observer-body");
  const auditBody = document.getElementById("audit-body");
  const executionPanel = document.getElementById("execution-panel");
  const executionState = document.getElementById("execution-state");
  const executionOutput = document.getElementById("execution-output");
  const executeButton = document.getElementById("execute-command");
  const executionField = document.getElementById("decision-execution");
  const sandboxField = document.getElementById("decision-sandbox");
  let currentCommand = "";
  let currentToken = "";

  const steps = {
    parse: document.getElementById("step-parse"),
    policy: document.getElementById("step-policy"),
    observer: document.getElementById("step-observer"),
    semantic: document.getElementById("step-semantic"),
    audit: document.getElementById("step-audit"),
  };

  function resetSteps() {
    Object.values(steps).forEach((step) => {
      step.classList.remove("is-pass", "is-block", "is-warn", "is-skip");
    });
  }

  function mark(step, tone, detail) {
    if (!step) return;
    step.classList.remove("is-pass", "is-block", "is-warn", "is-skip");
    step.classList.add(tone);
    const node = step.querySelector(".trace-detail");
    if (node && detail) node.textContent = detail;
  }

  function text(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
  }

  function showObserver(observation) {
    observerBody.replaceChildren();
    if (!observation || typeof observation !== "object") {
      const p = document.createElement("p");
      p.className = "muted";
      p.textContent = "No observation recorded.";
      observerBody.append(p);
      return;
    }
    const statusValue = text(observation.status);
    const summary = document.createElement("p");
    summary.className = "evidence-summary";
    summary.textContent = `Status: ${statusValue} · mode: ${text(observation.mode)} · latency: ${text(
      observation.latency_ms
    )} ms`;
    observerBody.append(summary);
    if (observation.requested_model) {
      const model = document.createElement("p");
      model.className = "muted mono";
      model.textContent = `model: ${observation.requested_model}`;
      observerBody.append(model);
    }
    const probabilities = observation.probabilities;
    if (probabilities && typeof probabilities === "object") {
      const list = document.createElement("dl");
      list.className = "probability-list";
      Object.entries(probabilities).forEach(([key, value]) => {
        const row = document.createElement("div");
        const dt = document.createElement("dt");
        dt.textContent = key.replaceAll("_", " ");
        const dd = document.createElement("dd");
        const bar = document.createElement("span");
        bar.className = "probability-bar";
        const fill = document.createElement("span");
        const percent = Math.round(Number(value) * 100);
        fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        bar.append(fill);
        const number = document.createElement("span");
        number.className = "mono";
        number.textContent = `${percent}%`;
        dd.append(bar, number);
        row.append(dt, dd);
        list.append(row);
      });
      observerBody.append(list);
    }
  }

  function showAudit(stats) {
    auditBody.replaceChildren();
    if (!stats || typeof stats !== "object") {
      const p = document.createElement("p");
      p.className = "muted";
      p.textContent = "Audit API unavailable.";
      auditBody.append(p);
      return;
    }
    const rows = [
      ["Total signed decisions", stats.total],
      ["Approved or terminal", stats.total - stats.rejected],
      ["Blocked", stats.rejected],
      ["Executed", stats.executed],
    ];
    rows.forEach(([label, value]) => {
      const row = document.createElement("div");
      row.className = "receipt-row";
      const key = document.createElement("span");
      key.textContent = label;
      const val = document.createElement("strong");
      val.textContent = text(value);
      row.append(key, val);
      auditBody.append(row);
    });
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = "Chain verified by guardian-lab doctor.";
    auditBody.append(note);
  }

  function render(data) {
    const decision = data.decision || {};
    const approved = decision.approved;
    const decisionSource = text(decision.intent_source);
    const isAllow = approved === true;
    resetSteps();
    mark(steps.parse, "is-pass", "accepted");
    mark(steps.policy, isAllow ? "is-pass" : "is-block", isAllow ? "passed" : "blocked");
    const observer = decision.system_one && typeof decision.system_one === "object" ? decision.system_one : {};
    const observerStatus = text(observer.status);
    if (observerStatus === "observed") mark(steps.observer, "is-pass", "observed");
    else if (observerStatus === "unavailable") mark(steps.observer, "is-warn", "unavailable");
    else mark(steps.observer, "is-skip", observerStatus);
    if (decisionSource === "llm") mark(steps.semantic, "is-pass", "used");
    else if (decisionSource === "llm_error") mark(steps.semantic, "is-block", "unavailable");
    else mark(steps.semantic, "is-skip", "not required");
    mark(steps.audit, "is-pass", `${data.audit ? data.audit.total : "?"} rows`);

    badge.textContent = isAllow ? "ALLOW" : "BLOCK";
    badge.className = `decision-badge ${isAllow ? "is-allow" : "is-block"}`;
    title.textContent = isAllow
      ? decisionSource === "llm"
        ? "Approved by semantic review"
        : "Approved by policy"
      : "Blocked by policy";
    reason.textContent = text(decision.reason);
    source.textContent = decisionSource;
    validationId.textContent = text(decision.validation_id);
    traceState.textContent = isAllow ? "Decision recorded" : "Rejection recorded";
    traceState.className = `chip ${isAllow ? "chip-ok" : "chip-block"}`;
    showObserver(observer);
    showAudit(data.audit);
    currentCommand = commandInput.value;
    currentToken = typeof decision.execution_token === "string" ? decision.execution_token : "";
    const canExecute = Boolean(data.executor && isAllow && currentToken);
    executionPanel.hidden = !canExecute;
    executionOutput.hidden = true;
    executionOutput.textContent = "";
    executionState.textContent = canExecute ? "Ready" : "Unavailable";
    executionState.className = `chip ${canExecute ? "chip-ok" : "chip-idle"}`;
    executionField.textContent = canExecute ? "Approved; run below" : "Not executed";
    if (canExecute && params.has("execute")) {
      executeButton.click();
    }
    sandboxField.textContent = data.executor
      ? "Hardened container, not a VM"
      : "Not configured in this demo";
  }

  async function run(payload) {
    submit.disabled = true;
    status.textContent = "Validating through Guardian...";
    try {
      const response = await fetch("/console/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }
      render(data);
      status.textContent = "Decision recorded. Nothing was executed.";
    } catch (error) {
      traceState.textContent = "Error";
      traceState.className = "chip chip-block";
      reason.textContent = error instanceof Error ? error.message : "Validation failed.";
      status.textContent = "Guardian did not return a decision.";
    } finally {
      submit.disabled = false;
    }
  }

  function loadScenario(index) {
    const scenario = scenarios[index];
    if (!scenario) return;
    taskInput.value = scenario.task;
    commandInput.value = scenario.command;
    untrustedInput.value = scenario.untrusted || "";
  }

  document.querySelectorAll(".scenario-btn").forEach((button) => {
    button.addEventListener("click", () => {
      loadScenario(Number(button.dataset.scenario));
      run({
        task: taskInput.value,
        command: commandInput.value,
        untrusted: untrustedInput.value,
      });
    });
  });

  executeButton.addEventListener("click", async () => {
    if (!currentCommand || !currentToken) return;
    executeButton.disabled = true;
    executionOutput.hidden = false;
    executionOutput.textContent = "Executing in the sandbox...";
    executionState.textContent = "Running";
    executionState.className = "chip chip-idle";
    try {
      const response = await fetch("/console/execute", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({command: currentCommand, token: currentToken}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      const output = [
        `status: ${data.status || "unknown"}  exit: ${data.exit_code ?? "?"}`,
        data.stdout ? `\n${data.stdout}` : "",
        data.stderr ? `\nstderr: ${data.stderr}` : "",
      ].join("");
      executionOutput.textContent = output || "No output.";
      executionState.textContent = data.exit_code === 0 ? "Completed" : "Finished with error";
      executionState.className = `chip ${data.exit_code === 0 ? "chip-ok" : "chip-block"}`;
      executionField.textContent = data.status || "executed";
      if (data.audit) showAudit(data.audit);
      if (data.warning) {
        executionOutput.textContent += `\nwarning: ${data.warning}`;
      }
    } catch (error) {
      executionOutput.textContent = error instanceof Error ? error.message : "Execution failed.";
      executionState.textContent = "Error";
      executionState.className = "chip chip-block";
    } finally {
      executeButton.disabled = false;
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    run({
      task: taskInput.value,
      command: commandInput.value,
      untrusted: untrustedInput.value,
    });
  });

  loadScenario(0);
  if (params.has("autorun")) {
    const scene = Math.max(0, Number(params.get("scene") || "0"));
    document.querySelectorAll(".scenario-btn")[scene]?.click();
  }
})();
