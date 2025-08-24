document.addEventListener("DOMContentLoaded", () => {
  // --- SCRIPT FOR CHAT PAGE ---
  // This code will only run if it finds an element with the id 'chat-form'
  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    const questionInput = document.getElementById("question");
    const askBtn = document.getElementById("ask-btn");
    const messageList = document.getElementById("message-list");
    const loadingChat = document.getElementById("loading-indicator-chat");
    const chatContainer = document.getElementById("chat-container");

    const handleChatSubmit = async (event) => {
      event.preventDefault();
      const question = questionInput.value.trim();
      if (!question) return;

      appendMessage("user", question);
      questionInput.value = "";
      setChatLoadingState(true);

      try {
        // Corrected: Using fetch with JSON, matching the /api/chat endpoint
        const response = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question }),
        });
        const data = await response.json();
        if (!response.ok)
          throw new Error(data.error || "A network error occurred.");
        appendMessage("ai", data.answer);
      } catch (error) {
        appendMessage("ai", `**Error:** ${error.message}`);
      } finally {
        setChatLoadingState(false);
      }
    };

    const appendMessage = (sender, content) => {
      const messageWrapper = document.createElement("div");
      messageWrapper.className = "message-wrapper";
      const messageDiv = document.createElement("div");
      messageDiv.className = sender === "user" ? "message-user" : "message-ai";
      const contentDiv = document.createElement("div");
      contentDiv.className = "message-content";
      // Use marked.parse for AI messages to render markdown, and create a simple <p> for user messages
      contentDiv.innerHTML =
        sender === "ai" ? marked.parse(content) : `<p>${content}</p>`;

      messageDiv.appendChild(contentDiv);
      messageWrapper.appendChild(messageDiv);
      messageList.appendChild(messageWrapper);
      chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    const setChatLoadingState = (isLoading) => {
      loadingChat.style.display = isLoading ? "block" : "none";
      askBtn.disabled = isLoading;
      questionInput.disabled = isLoading;
      if (!isLoading) questionInput.focus();
    };

    // Auto-resize textarea
    questionInput.addEventListener("input", () => {
      questionInput.style.height = "auto";
      questionInput.style.height = `${questionInput.scrollHeight}px`;
    });

    chatForm.addEventListener("submit", handleChatSubmit);
    questionInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleChatSubmit(event);
      }
    });
  }
  // --- SCRIPT FOR SUMMARISE PAGE ---
  const summariseForm = document.getElementById("summarise-form");
  if (summariseForm) {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileSelectBtn = document.getElementById("file-select-btn");
    const documentTextArea = document.getElementById("document-text");
    const summariseBtn = document.getElementById("summarise-btn");
    const loadingSummary = document.getElementById("loading-indicator-summary");
    const summaryOutput = document.getElementById("summary-output");

    // --- CHANGE 1: Create a variable to hold the selected file ---
    let selectedFile = null;

    const handleSummariseSubmit = async (event) => {
      event.preventDefault();

      // --- CHANGE 2: Check if a file has been selected ---
      if (!selectedFile) {
        summaryOutput.innerHTML = marked.parse(
          `**Error:** Please select a file first.`
        );
        summaryOutput.classList.remove("hidden");
        return;
      }

      setSummaryLoadingState(true);

      // --- CHANGE 3: Use FormData to send the file ---
      const formData = new FormData();
      formData.append("file", selectedFile); // The key 'file' must match request.files['file'] in Flask

      try {
        // --- CHANGE 4: Update the fetch request ---
        // The body is now formData, and we REMOVE the Content-Type header.
        // The browser will automatically set it to multipart/form-data.
        const response = await fetch("/summarize", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();
        if (!response.ok)
          throw new Error(data.error || "A network error occurred.");

        summaryOutput.innerHTML = marked.parse(data.summary);
        summaryOutput.classList.remove("hidden");
      } catch (error) {
        summaryOutput.innerHTML = marked.parse(`**Error:** ${error.message}`);
        summaryOutput.classList.remove("hidden");
      } finally {
        setSummaryLoadingState(false);
      }
    };

    const setSummaryLoadingState = (isLoading) => {
      loadingSummary.style.display = isLoading ? "block" : "none";
      summariseBtn.disabled = isLoading;
      if (isLoading) summaryOutput.classList.add("hidden");
    };

    // This function can stay, as showing the text in the UI is good UX.
    const handleFile = (file) => {
      if (!file) return;

      // --- CHANGE 5: Store the file for submission ---
      selectedFile = file;

      const reader = new FileReader();
      reader.onload = (e) => {
        documentTextArea.value = e.target.result;
        summariseBtn.disabled = false;
      };
      reader.onerror = () => {
        documentTextArea.value = "Error: Could not read the selected file.";
        selectedFile = null; // Clear the file if it can't be read
      };
      reader.readAsText(file);
    };

    // --- All event listeners below this line can remain exactly the same ---
    fileSelectBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));

    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        (e) => {
          e.preventDefault();
          e.stopPropagation();
        },
        false
      );
    });
    ["dragenter", "dragover"].forEach((eventName) =>
      dropZone.addEventListener(eventName, () =>
        dropZone.classList.add("drag-over")
      )
    );
    ["dragleave", "drop"].forEach((eventName) =>
      dropZone.addEventListener(eventName, () =>
        dropZone.classList.remove("drag-over")
      )
    );
    dropZone.addEventListener(
      "drop",
      (e) => handleFile(e.dataTransfer.files[0]),
      false
    );
    summariseForm.addEventListener("submit", handleSummariseSubmit);
  }
});
