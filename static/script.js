document.addEventListener("DOMContentLoaded", () => {
  const chatArea = document.getElementById("chat-area");
  const chatBox = document.getElementById("chat-box");
  const input = document.getElementById("user-input");
  const clearBtn = document.getElementById("clear-btn");
  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const analyticsBtn = document.getElementById("analytics-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const voiceSelect = document.getElementById("voice-select");
  const speechBtn = document.getElementById("speech-btn");
  const themeToggle = document.getElementById("themeToggle");

  let speechOn = true;
  let recognition, isRecording = false;
  let ttsEnabled = false;
  let voices = [];
  let languages = [];
  let speechLang = "";
  let currentSessionId = null;  // Track current conversation session
  let currentAbortController = null;  // For cancelling ongoing requests
  let isGenerating = false;  // Track if response is being generated

  // ===== Helper Functions =====
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ===== Markdown Parser =====
  function parseMarkdown(text) {
    // Use marked.js if available, otherwise basic parsing
    if (typeof marked !== 'undefined') {
      // Configure marked to open links in new tab
      const renderer = new marked.Renderer();
      renderer.link = function(href, title, text) {
        // Handle both old and new marked.js API
        if (typeof href === 'object') {
          // New API: href is an object with href, title, text properties
          const link = href;
          return `<a href="${link.href}" target="_blank" rel="noopener noreferrer"${link.title ? ` title="${link.title}"` : ''}>${link.text}</a>`;
        }
        // Old API: separate parameters
        return `<a href="${href}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${text}</a>`;
      };
      
      marked.setOptions({
        breaks: true,
        gfm: true,
        renderer: renderer
      });
      return marked.parse(text);
    }
    
    // Fallback: basic markdown to HTML conversion
    let html = text
      // Escape HTML first
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Code blocks (```...```)
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
      // Inline code (`...`)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Bold (**...**)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // Italic (*...*)
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      // Headers (# ... ## ... ### ...)
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      // Unordered lists (- item)
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      // Ordered lists (1. item)
      .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
      // Links [text](url)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      // Line breaks
      .replace(/\n/g, '<br>');
    
    // Wrap consecutive <li> tags in <ul>
    html = html.replace(/(<li>.*?<\/li>)(<br>)?(<li>)/g, '$1$3');
    html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');
    
    return html;
  }

  // ===== Mobile Sidebar Toggle =====
  const menuToggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const sidebarOverlay = document.getElementById("sidebar-overlay");

  function openSidebar() {
    sidebar.classList.add("open");
    sidebarOverlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarOverlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (menuToggle) {
    menuToggle.addEventListener("click", openSidebar);
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", closeSidebar);
  }

  // Close sidebar when clicking a ribbon button (mobile)
  document.querySelectorAll(".ribbon-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (window.innerWidth <= 768) {
        closeSidebar();
      }
    });
  });

  // Close sidebar when clicking a history item (mobile)
  document.addEventListener("click", (e) => {
    if (e.target.closest(".history-item") && window.innerWidth <= 768) {
      closeSidebar();
    }
  });

  // ===== Theme Toggle =====
  function initTheme() {
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);
  }

  function updateThemeIcon(theme) {
    if (themeToggle) {
      themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
      themeToggle.title = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
    }
  }

  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    updateThemeIcon(newTheme);
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme);
  }
  initTheme();

  speechBtn.addEventListener("click", () => {
    // If currently speaking, stop it
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      speechBtn.textContent = "🔈";
      speechBtn.title = "Speech stopped";
      speechBtn.classList.remove("speaking");
      speechBtn.classList.add("stopped");
      setTimeout(() => speechBtn.classList.remove("stopped"), 500);
      
      // Update any active read-aloud buttons
      document.querySelectorAll(".read-aloud-btn.speaking").forEach(btn => {
        btn.classList.remove("speaking");
        btn.innerHTML = "🔊";
        btn.title = "Read aloud";
      });
      
      showAudioFeedback("Speech stopped", "⏹️", "stopped");
      playAudioCue('stop');
      return;
    }
    
    // Toggle speech on/off
    speechOn = !speechOn;
    speechBtn.textContent = speechOn ? "🔈" : "🔇";
    speechBtn.title = speechOn ? "Mute speech" : "Unmute speech";
    
    if (speechOn) {
      speechBtn.classList.remove("muted");
      showAudioFeedback("Speech enabled", "🔊", "unmuted");
      playAudioCue('unmute');
    } else {
      speechBtn.classList.add("muted");
      showAudioFeedback("Speech muted", "🔇", "muted");
      playAudioCue('mute');
    }
  });

  function writeMessage(text, cls = "bot") {
    const msg = document.createElement("div");
    msg.className = `chat-message ${cls}-message`;
    
    // Create content wrapper
    const contentWrapper = document.createElement("div");
    contentWrapper.className = "message-content";
    contentWrapper.innerText = text;
    msg.appendChild(contentWrapper);
    
    // Add read aloud button for bot messages
    if (cls === "bot") {
      const actionsDiv = document.createElement("div");
      actionsDiv.className = "message-actions";
      
      const readBtn = document.createElement("button");
      readBtn.className = "read-aloud-btn";
      readBtn.innerHTML = "🔊";
      readBtn.title = "Read aloud";
      readBtn.addEventListener("click", () => {
        speakMessage(contentWrapper.innerText || contentWrapper.textContent, readBtn);
      });
      
      actionsDiv.appendChild(readBtn);
      msg.appendChild(actionsDiv);
    }
    
    chatBox.appendChild(msg);
    chatArea.scrollTop = chatBox.scrollHeight;
    return msg;
  }

  function speakMessage(text, button) {
    // If this button is already speaking, stop it
    if (button && button.classList.contains("speaking")) {
      window.speechSynthesis.cancel();
      button.classList.remove("speaking");
      button.innerHTML = "🔊";
      button.title = "Read aloud";
      return;
    }
    
    // Stop any current speech
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      // Reset all other speaking buttons
      document.querySelectorAll(".read-aloud-btn.speaking").forEach(btn => {
        btn.classList.remove("speaking");
        btn.innerHTML = "🔊";
        btn.title = "Read aloud";
      });
    }
    
    // Clean text for speech (remove HTML, markdown, etc.)
    const cleanText = cleanTextForSpeech(text);
    
    const utter = new SpeechSynthesisUtterance(cleanText);
    
    // Use selected voice from dropdown
    const selectedIndex = parseInt(voiceSelect.value, 10);
    if (voices && voices.length > 0 && selectedIndex >= 0 && selectedIndex < voices.length) {
      utter.voice = voices[selectedIndex];
      utter.lang = voices[selectedIndex].lang;
    }
    
    // Mark button as speaking and update speech button
    if (button) {
      button.classList.add("speaking");
      button.innerHTML = "⏹️";
      button.title = "Stop reading";
    }
    speechBtn.classList.add("speaking");
    
    utter.onstart = () => {
      showAudioFeedback("Reading aloud...", "🔊", "speaking");
    };
    
    utter.onend = () => {
      if (button) {
        button.classList.remove("speaking");
        button.innerHTML = "🔊";
        button.title = "Read aloud";
      }
      speechBtn.classList.remove("speaking");
    };
    
    utter.onerror = () => {
      if (button) {
        button.classList.remove("speaking");
        button.innerHTML = "🔊";
        button.title = "Read aloud";
      }
      speechBtn.classList.remove("speaking");
    };
    
    speechSynthesis.speak(utter);
  }

  function createLoadingIndicator() {
    const loading = document.createElement("div");
    loading.className = "loading-indicator";
    loading.id = "loading-indicator";
    loading.innerHTML = `
      <span>Thinking</span>
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
    `;
    chatBox.appendChild(loading);
    chatArea.scrollTop = chatBox.scrollHeight;
    return loading;
  }

  function removeLoadingIndicator() {
    const loading = document.getElementById("loading-indicator");
    if (loading) loading.remove();
  }

  function showStopButton() {
    isGenerating = true;
    sendBtn.innerHTML = "⏹️";
    sendBtn.title = "Stop generation";
    sendBtn.classList.add("stop-mode");
  }

  function hideStopButton() {
    isGenerating = false;
    sendBtn.innerHTML = "🚀";
    sendBtn.title = "Send message";
    sendBtn.classList.remove("stop-mode");
    currentAbortController = null;
  }

  function stopGeneration() {
    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }
    removeLoadingIndicator();
    clearProcessSteps();
    hideStopButton();
    
    // Add a note that generation was stopped
    const stoppedMsg = document.createElement("div");
    stoppedMsg.className = "generation-stopped";
    stoppedMsg.innerHTML = "<em>⏹️ Generation stopped</em>";
    chatBox.appendChild(stoppedMsg);
    chatArea.scrollTop = chatBox.scrollHeight;
  }

  function createToolIndicator(toolName, isStart = true) {
    const toolNames = {
      "search_documents": "🔍 Searching documents",
      "list_uploaded_documents": "📂 Listing documents",
      "list_employees": "👥 Fetching employees",
      "get_employee": "👤 Getting employee details",
      "list_projects": "📋 Fetching projects",
      "get_project": "📁 Getting project details",
      "list_tasks": "✅ Fetching tasks",
      "get_task": "📝 Getting task details",
      "create_employee": "➕ Creating employee",
      "create_project": "➕ Creating project",
      "create_task": "➕ Creating task",
      "delete_employee": "🗑️ Deleting employee",
      "delete_project": "🗑️ Deleting project",
      "delete_task": "🗑️ Deleting task",
      "clear_uploaded_documents": "🧹 Clearing documents"
    };

    const displayName = toolNames[toolName] || `🔧 ${toolName}`;
    const indicator = document.createElement("div");
    indicator.className = `tool-indicator${isStart ? "" : " completed"}`;
    indicator.dataset.tool = toolName;
    
    if (isStart) {
      indicator.innerHTML = `
        <div class="tool-spinner"></div>
        <span>${displayName}...</span>
      `;
    } else {
      indicator.innerHTML = `
        <span class="tool-icon">✓</span>
        <span>${displayName}</span>
      `;
    }
    
    // Find or create process steps container
    let stepsContainer = document.getElementById("process-steps");
    if (!stepsContainer) {
      stepsContainer = document.createElement("div");
      stepsContainer.className = "process-steps";
      stepsContainer.id = "process-steps";
      chatBox.appendChild(stepsContainer);
    }
    
    stepsContainer.appendChild(indicator);
    chatArea.scrollTop = chatBox.scrollHeight;
    return indicator;
  }

  function updateToolIndicator(toolName) {
    const indicators = document.querySelectorAll(`[data-tool="${toolName}"]`);
    indicators.forEach(indicator => {
      indicator.className = "tool-indicator completed";
      const text = indicator.querySelector("span:last-child")?.textContent?.replace("...", "") || toolName;
      indicator.innerHTML = `
        <span class="tool-icon">✓</span>
        <span>${text}</span>
      `;
    });
  }

  function minimizeProcessSteps() {
    // Convert process steps to minimized tool summary attached to the bot message
    const steps = document.getElementById("process-steps");
    if (steps && steps.children.length > 0) {
      const tools = Array.from(steps.children).map(el => el.dataset.tool);
      steps.remove();
      return tools;
    }
    return [];
  }

  function createToolSummary(tools, messageDiv) {
    if (!tools || tools.length === 0) return;
    
    const toolNames = {
      "search_documents": "🔍 Doc Search",
      "list_uploaded_documents": "📂 List Docs",
      "list_employees": "👥 Employees",
      "get_employee": "👤 Employee",
      "list_projects": "📋 Projects",
      "get_project": "📁 Project",
      "list_tasks": "✅ Tasks",
      "get_task": "📝 Task",
      "create_employee": "➕ Create Emp",
      "create_project": "➕ Create Proj",
      "create_task": "➕ Create Task",
      "delete_employee": "🗑️ Del Emp",
      "delete_project": "🗑️ Del Proj",
      "delete_task": "🗑️ Del Task",
      "clear_uploaded_documents": "🧹 Clear Docs"
    };

    const summary = document.createElement("div");
    summary.className = "tool-summary";
    summary.innerHTML = `<span class="tool-summary-label">Tools used:</span>`;
    
    tools.forEach(tool => {
      const badge = document.createElement("span");
      badge.className = "tool-indicator minimized";
      badge.innerHTML = `<span class="tool-icon">✓</span> ${toolNames[tool] || tool}`;
      summary.appendChild(badge);
    });
    
    messageDiv.appendChild(summary);
  }

  function clearProcessSteps() {
    const steps = document.getElementById("process-steps");
    if (steps) steps.remove();
  }

  // ===== Voice Management =====
  const VOICE_STORAGE_KEY = "selectedVoiceIndex";
  let selectedVoiceIndex = 0;

  function loadSavedVoice() {
    const saved = localStorage.getItem(VOICE_STORAGE_KEY);
    if (saved !== null) {
      selectedVoiceIndex = parseInt(saved, 10);
    }
  }

  function saveVoice(index) {
    localStorage.setItem(VOICE_STORAGE_KEY, index);
    selectedVoiceIndex = index;
  }

  function setVoiceAndLanguage() {
    const index = parseInt(voiceSelect.value, 10);
    saveVoice(index);
    if (recognition && voices[index]) {
      recognition.lang = voices[index].lang;
    }
  }

  function populateVoices() {
    // Get all available voices
    voices = speechSynthesis.getVoices();
    
    if (voices.length === 0) {
      // Voices not loaded yet, wait for them
      return;
    }
    
    // Load saved preference
    loadSavedVoice();
    
    // Group voices by language for better organization
    const voicesByLang = {};
    voices.forEach((v, i) => {
      const lang = v.lang.split('-')[0];
      if (!voicesByLang[lang]) voicesByLang[lang] = [];
      voicesByLang[lang].push({ voice: v, index: i });
    });
    
    // Build options with language groups
    let optionsHtml = '';
    
    // Sort languages alphabetically
    const sortedLangs = Object.keys(voicesByLang).sort();
    
    sortedLangs.forEach(lang => {
      const langVoices = voicesByLang[lang];
      // Sort voices within language by name
      langVoices.sort((a, b) => a.voice.name.localeCompare(b.voice.name));
      
      langVoices.forEach(({ voice, index }) => {
        const isDefault = voice.default ? ' ★' : '';
        const isLocal = voice.localService ? '' : ' (online)';
        optionsHtml += `<option value="${index}">${voice.name} (${voice.lang})${isDefault}${isLocal}</option>`;
      });
    });
    
    voiceSelect.innerHTML = optionsHtml;
    
    // Restore saved selection (validate it still exists)
    if (selectedVoiceIndex >= 0 && selectedVoiceIndex < voices.length) {
      voiceSelect.value = selectedVoiceIndex;
    } else {
      // Find a good default (prefer local English voice)
      const defaultIndex = voices.findIndex(v => v.default) || 
                          voices.findIndex(v => v.lang.startsWith('en') && v.localService) ||
                          0;
      voiceSelect.value = defaultIndex;
      saveVoice(defaultIndex);
    }
    
    // Update recognition language
    if (recognition && voices[voiceSelect.value]) {
      recognition.lang = voices[voiceSelect.value].lang;
    }
    
    languages = voices.map(v => v.lang);
  }

  voiceSelect.addEventListener("change", setVoiceAndLanguage);
  
  // Voices load asynchronously - handle both sync and async loading
  if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = populateVoices;
  }
  
  // Try loading immediately (some browsers have voices ready)
  populateVoices();
  
  // Also try after a short delay (fallback for some browsers)
  setTimeout(populateVoices, 100);
  setTimeout(populateVoices, 1000);

  // ===== Audio Feedback System =====
  function showAudioFeedback(message, icon, type) {
    // Remove any existing feedback
    const existing = document.querySelector('.audio-feedback');
    if (existing) existing.remove();
    
    const feedback = document.createElement('div');
    feedback.className = `audio-feedback ${type}`;
    
    if (type === 'recording') {
      feedback.innerHTML = `
        <span class="feedback-icon">${icon}</span>
        <span>${message}</span>
        <div class="sound-wave">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
      `;
    } else {
      feedback.innerHTML = `
        <span class="feedback-icon">${icon}</span>
        <span>${message}</span>
      `;
    }
    
    document.body.appendChild(feedback);
    
    // Auto-remove after animation completes
    setTimeout(() => {
      if (feedback.parentNode) feedback.remove();
    }, 2000);
  }

  // Play a subtle sound effect
  function playAudioCue(type) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    switch(type) {
      case 'start':
        oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(1100, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialDecayTo && gainNode.gain.exponentialDecayTo(0.01, audioContext.currentTime + 0.2);
        break;
      case 'stop':
        oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        break;
      case 'success':
        oscillator.frequency.setValueAtTime(523, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(659, audioContext.currentTime + 0.1);
        oscillator.frequency.setValueAtTime(784, audioContext.currentTime + 0.2);
        gainNode.gain.setValueAtTime(0.08, audioContext.currentTime);
        break;
      case 'mute':
        oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(330, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.08, audioContext.currentTime);
        break;
      case 'unmute':
        oscillator.frequency.setValueAtTime(330, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(440, audioContext.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.08, audioContext.currentTime);
        break;
    }
    
    oscillator.type = 'sine';
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.25);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
  }

  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => { 
      isRecording = true; 
      micBtn.classList.add("active");
      micBtn.innerHTML = "🎤";
      micBtn.title = "Listening... Click to stop";
      showAudioFeedback("Listening...", "🎤", "recording");
      playAudioCue('start');
    };
    
    recognition.onend = () => { 
      isRecording = false; 
      micBtn.classList.remove("active");
      micBtn.innerHTML = "🎙️";
      micBtn.title = "Use microphone";
    };
    
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript.trim();
      input.value = transcript;
      ttsEnabled = true;
      showAudioFeedback("Got it!", "✅", "listening");
      playAudioCue('success');
      sendMessage();
    };
    
    recognition.onerror = (e) => {
      isRecording = false;
      micBtn.classList.remove("active");
      micBtn.innerHTML = "🎙️";
      micBtn.title = "Use microphone";
      if (e.error !== 'aborted') {
        showAudioFeedback("Couldn't hear you", "❌", "stopped");
      }
    };

    micBtn.addEventListener("click", () => {
      if (isRecording) {
        recognition.stop();
        showAudioFeedback("Stopped listening", "⏹️", "stopped");
        playAudioCue('stop');
      } else {
        recognition.start();
      }
    });
  } else {
    // Browser doesn't support speech recognition
    micBtn.style.opacity = "0.5";
    micBtn.title = "Speech recognition not supported";
    micBtn.disabled = true;
  }

  function getSelectedVoice() {
    const index = parseInt(voiceSelect.value, 10);
    if (voices && voices.length > 0 && index >= 0 && index < voices.length) {
      return voices[index];
    }
    return null;
  }

  // Clean text for speech - remove markdown formatting and HTML
  function cleanTextForSpeech(text) {
    return text
      // Remove HTML tags
      .replace(/<[^>]*>/g, ' ')
      // Remove markdown code blocks
      .replace(/```[\s\S]*?```/g, ' code block ')
      // Remove inline code
      .replace(/`([^`]+)`/g, '$1')
      // Remove bold/italic markers (**, *, __, _)
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/__([^_]+)__/g, '$1')
      .replace(/_([^_]+)_/g, '$1')
      // Remove headers (#)
      .replace(/^#{1,6}\s*/gm, '')
      // Remove link markdown [text](url) -> text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Remove image markdown ![alt](url)
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
      // Remove blockquotes
      .replace(/^>\s*/gm, '')
      // Remove horizontal rules
      .replace(/^[-*_]{3,}\s*$/gm, '')
      // Remove list markers (-, *, +, 1.)
      .replace(/^[\s]*[-*+]\s+/gm, '')
      .replace(/^[\s]*\d+\.\s+/gm, '')
      // Remove extra whitespace
      .replace(/\s+/g, ' ')
      .trim();
  }

  function speak(text) {
    if (!speechOn) return;
    
    const cleanText = cleanTextForSpeech(text);
    
    const utter = new SpeechSynthesisUtterance(cleanText);
    const selectedVoice = getSelectedVoice();
    if (selectedVoice) {
      utter.voice = selectedVoice;
      utter.lang = selectedVoice.lang;
    }
    
    // Visual feedback when speaking starts
    utter.onstart = () => {
      speechBtn.classList.add("speaking");
    };
    
    utter.onend = () => {
      speechBtn.classList.remove("speaking");
    };
    
    utter.onerror = () => {
      speechBtn.classList.remove("speaking");
    };
    
    speechSynthesis.speak(utter);
  }

  async function sendMessage() {
    // If currently generating, stop instead of sending
    if (isGenerating) {
      stopGeneration();
      return;
    }

    const text = input.value.trim();
    input.value = "";
    if (!text) return;

    writeMessage(text, "user");
    createLoadingIndicator();
    showStopButton();
    
    // Create abort controller for this request
    currentAbortController = new AbortController();
    const signal = currentAbortController.signal;
    
    let fullResponse = "";
    let toolsUsed = [];

    try {
      console.log("Sending message with session_id:", currentSessionId);
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ user_input: text, session_id: currentSessionId }),
        signal: signal
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let botMsgDiv = null;
      let hasContent = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          removeLoadingIndicator();
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");

        for (let i = 0; i < parts.length - 1; i++) {
          const part = parts[i].trim();
          if (part.startsWith("data:")) {
            try {
              const data = JSON.parse(part.slice(5).trim());
              
              // Handle tool start
              if (data.tool_start) {
                removeLoadingIndicator();
                toolsUsed.push(data.tool_start);
                createToolIndicator(data.tool_start, true);
              }
              
              // Handle tool end
              if (data.tool_end) {
                updateToolIndicator(data.tool_end);
              }
              
              // Handle content
              if (data.content) {
                if (!hasContent) {
                  removeLoadingIndicator();
                  minimizeProcessSteps(); // Remove live indicators
                  botMsgDiv = writeMessage("", "bot");
                  hasContent = true;
                }
                fullResponse += data.content;
                // Show raw text while streaming (in content wrapper)
                const contentEl = botMsgDiv.querySelector(".message-content");
                if (contentEl) {
                  contentEl.innerText = fullResponse;
                }
                chatArea.scrollTop = chatBox.scrollHeight;
              }
              
              if (data.done) {
                hideStopButton();
                // Parse markdown to HTML when complete
                if (botMsgDiv && fullResponse) {
                  const contentEl = botMsgDiv.querySelector(".message-content");
                  if (contentEl) {
                    contentEl.innerHTML = parseMarkdown(fullResponse);
                  }
                }
                // Attach tool summary
                if (botMsgDiv && toolsUsed.length > 0) {
                  createToolSummary(toolsUsed, botMsgDiv);
                }
                speak(fullResponse);
                loadHistoryList();
              }
              if (data.error) {
                hideStopButton();
                removeLoadingIndicator();
                clearProcessSteps();
                writeMessage("Error: " + data.error, "bot");
              }
            } catch (e) {
              console.error("Parse error", e, part);
            }
          }
        }
        buffer = parts[parts.length - 1];
      }
    } catch (err) {
      hideStopButton();
      removeLoadingIndicator();
      clearProcessSteps();
      
      // Don't show error for aborted requests
      if (err.name === 'AbortError') {
        console.log('Request was aborted');
      } else {
        writeMessage("Error connecting to server.", "bot");
        console.error(err);
      }
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter") sendMessage(); });

  newChatBtn.addEventListener("click", startNewChat);

  async function startNewChat() {
    try {
      // Reset session on the server - new session created on first message
      const res = await fetch("/api/conversations/sessions/new", {
        method: "POST"
      });
      const data = await res.json();
      
      if (data.success) {
        currentSessionId = null;  // Will be created on first message with proper preview
        const chatBox = document.getElementById("chat-box");
        if (chatBox) chatBox.innerHTML = "";
        // Refresh history list
        loadHistoryList();
      }
    } catch (err) {
      console.error("Error starting new chat:", err);
    }
  }

  async function logout() {
    try {
      const res = await fetch("/logout", {
        method: "POST",
        credentials: "same-origin"
      });

      if (res.redirected) {
        window.location.href = res.url;
      } else {
        window.location.reload();
      }
    } catch (err) {
      console.error("Logout failed:", err);
    }
  }

  document.getElementById("logout-btn").addEventListener("click", logout);

  async function analytics() {
    try {
      const response = await fetch('/analytics', { method: 'POST' });
      const data = await response.json();
      chatBox.innerHTML = '';

      const totalsDiv = document.createElement('div');
      totalsDiv.classList.add('analytics-totals');
      totalsDiv.innerHTML = `
        <p>Total Employees: ${data.total_employees}</p>
        <p>Total Projects: ${data.total_projects}</p>
        <p>Total Tasks: ${data.total_tasks}</p>
      `;
      chatBox.appendChild(totalsDiv);

      const charts = [
        {
          title: 'Employees by Department',
          type: 'pie',
          labels: Object.keys(data.employees_per_department),
          values: Object.values(data.employees_per_department)
        },
        {
          title: 'Tasks by Status',
          type: 'bar',
          labels: Object.keys(data.tasks_per_status),
          values: Object.values(data.tasks_per_status)
        }
      ];

      for (const chartInfo of charts) {
        const title = document.createElement('h3');
        title.textContent = chartInfo.title;
        chatBox.appendChild(title);

        const canvas = document.createElement('canvas');
        chatBox.appendChild(canvas);
        canvas.style.width = '550px';

        new Chart(canvas, {
          type: chartInfo.type,
          data: {
            labels: chartInfo.labels,
            datasets: [{
              label: chartInfo.title,
              data: chartInfo.values,
              backgroundColor: chartInfo.type === 'pie' ? generateColors(chartInfo.values.length) : 'rgba(54, 162, 235, 0.6)',
              borderColor: chartInfo.type === 'pie' ? '#fff' : 'rgba(54, 162, 235, 1)',
              borderWidth: 1
            }]
          },
          options: {
            responsive: false,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: chartInfo.type === 'pie' },
              title: { display: true, text: chartInfo.title, font: { size: 20 } }
            },
            scales: chartInfo.type === 'bar' ? { y: { beginAtZero: true, precision: 0 } } : {}
          }
        });
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
      chatBox.textContent = 'Failed to load analytics.';
    }
  }

  function generateColors(count) {
    return Array.from({ length: count }, () => {
      const r = Math.floor(Math.random() * 255);
      const g = Math.floor(Math.random() * 255);
      const b = Math.floor(Math.random() * 255);
      return `rgba(${r}, ${g}, ${b}, 0.6)`;
    });
  }

  analyticsBtn.addEventListener("click", analytics);

  // ===== File Upload for RAG =====
  const uploadBtn = document.getElementById("upload-btn");
  const fileInput = document.getElementById("file-input");

  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      writeMessage(`📎 Uploading ${file.name}...`, "user");
      createLoadingIndicator();

      try {
        const res = await fetch("/api/upload", {
          method: "POST",
          body: formData
        });

        const result = await res.json();
        removeLoadingIndicator();
        
        if (result.error) {
          writeMessage(`❌ Upload failed: ${result.error}`, "bot");
        } else {
          writeMessage(`✅ Successfully uploaded "${result.file}". Created ${result.chunks_count} searchable chunks.`, "bot");
          
          // Auto-ask about the document
          setTimeout(() => {
            input.value = `What is this document "${result.file}" about? Give me a summary.`;
            sendMessage();
          }, 500);
        }
      } catch (err) {
        removeLoadingIndicator();
        writeMessage(`❌ Upload error: ${err.message}`, "bot");
      }

      fileInput.value = "";
    });
  }

  // ===== Fetch and display user access level =====
  async function displayAccessLevel() {
    try {
      const res = await fetch("/api/user/access");
      const data = await res.json();
      const accessBadge = document.getElementById("access-badge");
      if (accessBadge) {
        const levelColors = { read: "#6b7280", write: "#3b82f6", admin: "#10b981" };
        accessBadge.textContent = data.level_name.toUpperCase();
        accessBadge.style.backgroundColor = levelColors[data.level_name] || "#6b7280";
      }
    } catch (err) {
      console.error("Failed to fetch access level:", err);
    }
  }
  displayAccessLevel();

  // ===== Conversation History Sidebar =====

  async function loadHistoryList() {
    const historyList = document.getElementById("history-list");
    if (!historyList) return;

    try {
      const res = await fetch("/api/conversations/sessions");
      const data = await res.json();
      
      // NEVER overwrite currentSessionId from server - user's selection takes priority
      // Only set it on initial page load when it's null AND we haven't loaded any sessions yet
      if (currentSessionId === null && data.current_session_id) {
        // Check if this is initial load (no history items exist yet)
        const existingItems = historyList.querySelectorAll('.history-item');
        if (existingItems.length === 0) {
          currentSessionId = data.current_session_id;
          console.log("Initial load - set currentSessionId from server:", currentSessionId);
        }
      }
      console.log("loadHistoryList - currentSessionId is:", currentSessionId);
      
      if (data.sessions && data.sessions.length > 0) {
        historyList.innerHTML = data.sessions.map(session => `
          <div class="history-item ${session.id === currentSessionId ? 'active' : ''}" data-session-id="${session.id}">
            <span class="history-icon">💬</span>
            <span class="history-text">${escapeHtml(session.preview) || 'New conversation'}</span>
            <span class="history-time">${formatTime(session.created_at)}</span>
            <button class="history-delete-btn" data-session-id="${session.id}" title="Delete conversation">🗑️</button>
          </div>
        `).join("");

        // Add click handlers for loading sessions
        historyList.querySelectorAll(".history-item").forEach(item => {
          item.addEventListener("click", (e) => {
            // Don't trigger if clicking delete button
            if (e.target.classList.contains("history-delete-btn")) return;
            const sessId = parseInt(item.dataset.sessionId, 10);
            loadSession(sessId);
          });
        });

        // Add click handlers for delete buttons
        historyList.querySelectorAll(".history-delete-btn").forEach(btn => {
          btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const sessId = parseInt(btn.dataset.sessionId, 10);
            if (confirm("Delete this conversation?")) {
              await deleteSession(sessId);
            }
          });
        });
      } else {
        historyList.innerHTML = '<div class="history-empty">No conversations yet</div>';
      }
    } catch (err) {
      console.error("Failed to load history:", err);
      historyList.innerHTML = '<div class="history-empty">Failed to load history</div>';
    }
  }

  async function deleteSession(sessionId) {
    try {
      const res = await fetch(`/api/conversations/sessions/${sessionId}`, {
        method: "DELETE"
      });
      const data = await res.json();
      
      if (data.success) {
        // If we deleted the current session, clear the chat
        if (sessionId === currentSessionId) {
          currentSessionId = null;
          chatBox.innerHTML = "";
          // Don't show a bot message - just clear the chat
        }
        loadHistoryList();
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  }

  async function startNewSession() {
    try {
      const res = await fetch("/api/conversations/sessions/new", {
        method: "POST"
      });
      const data = await res.json();
      
      if (data.success) {
        currentSessionId = null;  // Will be set when first message is sent
        console.log("startNewSession - cleared currentSessionId, new session will be created on first message");
        chatBox.innerHTML = "";
        // Don't show a bot message - just clear the chat
        loadHistoryList();
      }
    } catch (err) {
      console.error("Failed to create new session:", err);
    }
  }

  function formatTime(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return "now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
    return date.toLocaleDateString();
  }

  async function loadSession(sessionId) {
    // Convert to integer
    const sessionIdInt = parseInt(sessionId, 10);
    chatBox.innerHTML = "";
    
    // Show loading state
    writeMessage("Loading conversation...", "bot");
    
    try {
      // First, switch session on server side to sync in-memory messages
      const switchRes = await fetch(`/api/conversations/sessions/${sessionIdInt}/switch`, {
        method: "POST"
      });
      
      if (!switchRes.ok) {
        throw new Error(`Failed to switch session: ${switchRes.status}`);
      }
      
      const switchData = await switchRes.json();
      currentSessionId = sessionIdInt;
      console.log("loadSession - switched to session:", currentSessionId);
      
      // Clear loading message
      chatBox.innerHTML = "";
      
      // Now load the conversation messages
      const res = await fetch(`/api/conversations?session_id=${sessionIdInt}&limit=100`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      
      console.log("Loaded session data:", data); // Debug log
      
      if (data.conversations && data.conversations.length > 0) {
        for (const conv of data.conversations) {
          if (conv.role === "user") {
            writeMessage(conv.content, "user");
          } else if (conv.role === "assistant") {
            const msg = writeMessage("", "bot");
            // Parse markdown for bot messages
            const contentEl = msg.querySelector(".message-content");
            if (contentEl) {
              contentEl.innerHTML = parseMarkdown(conv.content);
            }
            if (conv.tool_name) {
              const tools = conv.tool_name.split(",").filter(t => t.trim());
              if (tools.length > 0) {
                createToolSummary(tools, msg);
              }
            }
          }
        }
        chatArea.scrollTop = chatBox.scrollHeight;
      } else {
        writeMessage("This conversation is empty. Start chatting!", "bot");
      }
      
      loadHistoryList(); // Refresh to show active state
    } catch (err) {
      console.error("Failed to load session:", err);
      chatBox.innerHTML = "";
      writeMessage("Failed to load conversation. Please try again.", "bot");
    }
  }

  // Refresh history button
  const refreshHistoryBtn = document.getElementById("refresh-history-btn");
  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", loadHistoryList);
  }

  // Load history sidebar on page load
  loadHistoryList();

  // ===== Load current session conversation on page load =====
  async function loadCurrentSession() {
    try {
      const res = await fetch("/api/conversations?limit=50");
      const data = await res.json();
      
      // Update currentSessionId from server response
      if (data.session_id) {
        currentSessionId = data.session_id;
        console.log("loadCurrentSession set currentSessionId to:", currentSessionId);
      }
      
      if (data.conversations && data.conversations.length > 0) {
        chatBox.innerHTML = ""; // Clear any existing content first
        for (const conv of data.conversations) {
          if (conv.role === "user") {
            writeMessage(conv.content, "user");
          } else if (conv.role === "assistant") {
            const msg = writeMessage("", "bot");
            // Parse markdown for bot messages
            const contentEl = msg.querySelector(".message-content");
            if (contentEl) {
              contentEl.innerHTML = parseMarkdown(conv.content);
            }
            if (conv.tool_name) {
              const tools = conv.tool_name.split(",").filter(t => t.trim());
              if (tools.length > 0) {
                createToolSummary(tools, msg);
              }
            }
          }
        }
        chatArea.scrollTop = chatBox.scrollHeight;
        // Refresh history to show active session
        loadHistoryList();
      }
    } catch (err) {
      console.error("Failed to load current session:", err);
    }
  }
  loadCurrentSession();

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== "Ctrl") input.focus();
  });

  clearBtn.addEventListener("click", () => {
    input.value = "";
  });
});
