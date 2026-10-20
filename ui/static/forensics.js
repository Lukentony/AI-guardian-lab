(() => {
    const form = document.getElementById("forensicsForm");
    const textarea = document.getElementById("jsonl_content");
    const fileInput = document.getElementById("fileInput");
    const uploadButton = document.getElementById("upload-button");
    const sampleButton = document.getElementById("load-sample");
    const status = document.getElementById("statusMsg");

    if (!form || !textarea || !fileInput || !uploadButton || !sampleButton || !status) {
        return;
    }

    const setStatus = (message, tone) => {
        status.textContent = message;
        status.style.color = tone === "error" ? "var(--danger)" : "var(--muted)";
    };

    const loadSample = async () => {
        sampleButton.disabled = true;
        setStatus("Loading example...", "info");
        try {
            const response = await fetch("/forensics/random_sample", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                throw new Error("Example unavailable");
            }
            const data = await response.json();
            textarea.value = data.content;
            setStatus("Loaded: " + data.name, "info");
        } catch (error) {
            setStatus("Could not load the example. Try again.", "error");
        } finally {
            sampleButton.disabled = false;
        }
    };

    const handleFile = (file) => {
        if (!file) {
            return;
        }
        const extension = file.name.split(".").pop().toLowerCase();
        if (extension !== "json" && extension !== "jsonl") {
            setStatus("Only .json or .jsonl files are accepted.", "error");
            fileInput.value = "";
            return;
        }
        if (file.size > 1024 * 1024) {
            setStatus("File too large. The limit is 1 MB.", "error");
            fileInput.value = "";
            return;
        }
        const reader = new FileReader();
        reader.onload = (event) => {
            textarea.value = event.target.result;
            setStatus("Loaded: " + file.name, "info");
        };
        reader.onerror = () => setStatus("Could not read the file.", "error");
        reader.readAsText(file);
    };

    uploadButton.addEventListener("click", () => fileInput.click());
    sampleButton.addEventListener("click", loadSample);
    fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));
})();
