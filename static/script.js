//document.addEventListener("DOMContentLoaded", () => {
//  const sendBtn = document.getElementById("send-btn");
//  const input = document.getElementById("user-input");
//  const chatBox = document.getElementById("chat-box");
//
//  function writeMessage(text, cls="bot") {
//    const p = document.createElement("div");
//    p.className = cls === "bot" ? "bot-message" : "user-message";
//    p.innerText = text;
//    chatBox.appendChild(p);
//    chatBox.scrollTop = chatBox.scrollHeight;
//  }
//
//  function appendMessage(text, cls="bot") {
//    botMessages = document.getElementsByClassName("bot-message");
//    lastBotMessage = botMessages[botMessages.length-1]
//    lastBotMessage.innerText += text;
////    chatBox.scrollTop = chatBox.scrollHeight;
//  }
//
//  sendBtn.addEventListener("click", async () => {
//    const text = input.value.trim();
//    if (!text) return;
//    writeMessage(text, "user");
//    input.value = "";
//
//    console.log(text);
//
//    // open SSE stream
//    const res = await fetch("/api/chat/stream", {
//      method: "POST",
//      headers: {"Content-Type": "application/json"},
//      body: JSON.stringify({ user_input: text })
////      body: text
//    });
//
//    // This endpoint returns text/event-stream; read as stream
//    const reader = res.body.getReader();
//    console.log(res);
//    const decoder = new TextDecoder();
//    let buffer = "";
//    writeMessage("", "bot");
//
//    while (true) {
//      const { value, done } = await reader.read();
//      if (done) break;
//      buffer += decoder.decode(value, { stream: true });
//      // each SSE frame is "data: {...}\n\n"
//      const parts = buffer.split("\n\n");
//      for (let i = 0; i < parts.length-1; i++) {
//        const part = parts[i].trim();
//        if (part.startsWith("data:")) {
//          const jsonText = part.slice(5).trim();
//          try {
//            const data = JSON.parse(jsonText);
//            if (data.content) {
//              appendMessage(data.content, "bot");
//            }
//            if (data.done) {
//              reader.cancel();
//              break;
//            }
//            if (data.error) {
//              writeMessage("Error: " + data.error, "bot");
//            }
//          } catch(e) {
//            console.error("Parse error", e, jsonText);
//          }
//        }
//      }
//      buffer = parts[parts.length-1];
//    }
//  });
//
//
//    const loginForm = document.getElementById("loginForm");
//  const registerForm = document.getElementById("registerForm");
//
//  if (loginForm) {
//    loginForm.addEventListener("submit", async (e) => {
//      e.preventDefault();
//      const username = document.getElementById("username").value;
//      const password = document.getElementById("password").value;
//
//      const res = await fetch("/api/login", {
//        method: "POST",
//        headers: {"Content-Type": "application/json"},
//        body: JSON.stringify({ username, password }),
//      });
//      const data = await res.json();
//      if (data.success) {
//        alert("Login successful!");
//        window.location.href = "/chat"; // Redirect to chat page
//      } else {
//        alert("Invalid credentials");
//      }
//    });
//  }
//
//  if (registerForm) {
//    registerForm.addEventListener("submit", async (e) => {
//      e.preventDefault();
//      const username = document.getElementById("username").value;
//      const password = document.getElementById("password").value;
//
//      const res = await fetch("/api/register", {
//        method: "POST",
//        headers: {"Content-Type": "application/json"},
//        body: JSON.stringify({ username, password }),
//      });
//      const data = await res.json();
//      if (data.success) {
//        alert("Registration successful!");
//        window.location.href = "/login";
//      } else {
//        alert("Registration failed");
//      }
//    });
//  }
//
//
//
//  input.addEventListener("keydown", (e) => {
//    if (e.key === "Enter") sendBtn.click();
//  });
//
//  document.addEventListener("keydown", (e) => {
//    if (e.key !== "Enter" || e.key !== "Ctrl") input.focus();
//  });
//
//});


/* script.js
   - New chat clears conversation
   - Logout calls /logout and redirects
   - Voice selection and recognition language selection
   - Speech recognition input triggers useVoice flag
   - SSE stream is consumed and only after 'done' the assistant speaks the full answer
*/

document.addEventListener("DOMContentLoaded", () => {
  // === DOM ELEMENTS ===
  const chatArea = document.getElementById("chat-area");
  const chatBox = document.getElementById("chat-box");
  const input = document.getElementById("user-input");
  const clearBtn = document.getElementById("clear-btn");
//  const clearBtn = document.getElementById("clear-btn");

  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const analyticsBtn = document.getElementById("analytics-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const voiceSelect = document.getElementById("voice-select");
  const langSelect = document.getElementById("lang-select");
  const speechBtn = document.getElementById("speech-btn");




  // === STATE ===
  let speechOn = true; // default state — speech enabled
  let recognition, isRecording = false;
  let ttsEnabled = false;
  let voices = [];
  let languages = [];
  speechLang = "";

  // === CHAT FUNCTIONS ===

  speechBtn.addEventListener("click", () => {
      speechOn = !speechOn;

      // Toggle icon
      speechBtn.textContent = speechOn ? "🔈" : "🔇";

      // Toggle tooltip
      speechBtn.title = speechOn ? "Mute speech" : "Unmute speech";

      // Optional: integrate with your TTS system
      if (speechOn) {
        console.log("Speech enabled");
        // e.g., enable speech synthesis here
      } else {
        console.log("Speech muted");
        // e.g., stop speech synthesis here
        if (window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
        }
      }
    });

  function writeMessage(text, cls = "bot") {
    const msg = document.createElement("div");
    msg.className = `chat-message ${cls}-message`;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatArea.scrollTop = chatBox.scrollHeight;
    return msg;
  }


  // === WEB SPEECH API ===
  function setVoiceAndLanguage() {
      if (recognition) {
//    langSelect.addEventListener("change", () => { recognition.lang = langSelect.value; });
        recognition.lang = languages[voiceSelect.value];
        console.log(recognition.lang);
    }
  }
  function populateVoices() {
    voices = speechSynthesis.getVoices();
    voiceSelect.innerHTML = voices.map((v, i) => `<option value="${i}" val="${v.lang}">${v.name} (${v.lang})</option>`).join("");
    console.log(voices);
    languages = voices.map((v) => v.lang);
    console.log(languages[1]);

    if (recognition) {
//    langSelect.addEventListener("change", () => { recognition.lang = langSelect.value; });
        recognition.lang = languages[voiceSelect.value];
        console.log(recognition.lang);
    }

    console.log(speechLang);
    voiceSelect.value = speechLang;
  }

  voiceSelect.addEventListener("change", () => {
    setVoiceAndLanguage();
  })
  speechSynthesis.onvoiceschanged = populateVoices;
  populateVoices();




  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => { isRecording = true; micBtn.classList.add("active"); };
    recognition.onend = () => { isRecording = false; micBtn.classList.remove("active"); };
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript.trim();
      input.value = transcript;
      ttsEnabled = true; // enable TTS for mic input
      sendMessage();
    };

    micBtn.addEventListener("click", () => {
      if (isRecording) recognition.stop();
      else recognition.start();
    });
  }

  function speak(text) {
    console.log("speak...");
//    if (!ttsEnabled) return;
    const utter = new SpeechSynthesisUtterance(text);
    const selected = voices[voiceSelect.value];
    speechLang = selected;
    console.log(speechLang);

    if (selected) utter.voice = selected;
    speechSynthesis.speak(utter);
    console.log(speechSynthesis.speaking);
//    while (window.speechSynthesis.speaking) {speechBtn.textContent = "🔊"};
    speechBtn.textContent = "🔈";

  }

  // === SEND MESSAGE ===
  async function sendMessage() {
    const text = input.value.trim();
    input.value = "";
    if (!text) return;

    writeMessage(text, "user");
//    chatArea.scrollTop = chatBox.scrollHeight;
    input.value = "";

    let fullResponse = "";
    writeMessage("...", "bot"); // placeholder for streaming

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ user_input: text })
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let botMsgDiv = chatBox.querySelector(".bot-message:last-child");

      while (true) {
        const { value, done } = await reader.read();
        if (done){
            console.log("finito");
            speak(fullResponse)
            break;

        }
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");

        for (let i = 0; i < parts.length - 1; i++) {
          const part = parts[i].trim();
          if (part.startsWith("data:")) {
            try {
              const data = JSON.parse(part.slice(5).trim());
              if (data.content) fullResponse += data.content;
              console.log(fullResponse);
              botMsgDiv.innerText = fullResponse; // replace placeholder

              if (data.done) {
//                botMsgDiv.innerText = fullResponse; // replace placeholder

                speak(fullResponse); // speak full response
                break;
              }
              if (data.error) botMsgDiv.innerText = "Error: " + data.error;
            } catch (e) {
              console.error("Parse error", e, part);
            }
          }
        }

        buffer = parts[parts.length - 1];
      }
    } catch (err) {
      writeMessage("Error connecting to server.", "bot");
      console.error(err);
    }
  }


  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter") sendMessage(); });

  // === NEW CHAT ===
  newChatBtn.addEventListener("click", () => {clearChat()});

  async function clearChat() {
      try {
        const res = await fetch("/clearcache", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_input: "clear" })
        });

        if (!res.ok) throw new Error("Failed to clear cache");

//        const data = await res.json();
//        console.log(data.message);

        // Optionally clear chat UI
        const chatBox = document.getElementById("chat-box");
        if (chatBox) chatBox.innerHTML = "";

        // Optional user feedback
        alert("Chat cache cleared!");
      } catch (err) {
        console.error("Error clearing chat:", err);
      }
    }


  // === LOGOUT ===
    async function logout() {
        try {
            const res = await fetch("/logout", {
                method: "POST",
                credentials: "same-origin" // ensures cookies are sent
            });

            if (res.redirected) {
                // If backend issues a redirect, follow it
                window.location.href = res.url;
            } else {
                // Otherwise, reload page to reflect logout
                window.location.reload();
            }
        } catch (err) {
            console.error("Logout failed:", err);
        }
    }

    // Example: bind to a logout button
   document.getElementById("logout-btn").addEventListener("click", logout);


//    const loginBtn = document.getElementById('login');
//    loginBtn.addEventListener('click', async (e) => {
//      e.preventDefault();
//      console.log("login");
//      const formData = new FormData(form);
//      const res = await fetch('/login', {
//        method: 'POST',
//        body: new URLSearchParams(formData)
//      });
//      if (res.redirected) {
//        window.location.href = res.url; // Redirect to index if successful
//      } else {
//        alert('Login failed. Check credentials.');
//      }
//    });




    async function analytics() {
    try {
        const response = await fetch('/analytics', { method: 'POST' });
        const data = await response.json();
        console.log(data);
        chatBox.innerHTML = '';

        // --- Totals ---
        const totalsDiv = document.createElement('div');
        totalsDiv.classList.add('analytics-totals');
        totalsDiv.innerHTML = `
            <p>Total Employees: ${data.total_employees}</p>
            <p>Total Projects: ${data.total_projects}</p>
            <p>Total Tasks: ${data.total_tasks}</p>
        `;
        chatBox.appendChild(totalsDiv);

        // --- Charts ---
        const charts = [];

        // Employees per department (pie chart)
        charts.push({
            title: 'Employees by Department',
            type: 'pie',
            labels: Object.keys(data.employees_per_department),
            values: Object.values(data.employees_per_department)
        });

        // Tasks per status (bar chart)
        charts.push({
            title: 'Tasks by Status',
            type: 'bar',
            labels: Object.keys(data.tasks_per_status),
            values: Object.values(data.tasks_per_status)
        });

        // Render charts
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
                    maintainAspectRatio: false, // ignore default aspect ratio
                    plugins: {
                        legend: { display: chartInfo.type === 'pie' },
                        title: { display: true, text: chartInfo.title, font: { size: 20 },  }
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

// Utility function for pie chart colors
    function generateColors(count) {
    return Array.from({ length: count }, () => {
        const r = Math.floor(Math.random() * 255);
        const g = Math.floor(Math.random() * 255);
        const b = Math.floor(Math.random() * 255);
        return `rgba(${r}, ${g}, ${b}, 0.6)`;
    });
}


   analyticsBtn.addEventListener("click", () => {
    analytics()
   })


  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendBtn.click();

    };

  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || e.key !== "Ctrl") input.focus();
  });

  clearBtn.addEventListener("click", (e) => {
    input.value = "";
  })

  // === LANGUAGE SELECTION ===
//  const languages = [
//    { code: "en-US", label: "English (US)" },
//    { code: "en-GB", label: "English (UK)" },
//    { code: "fr-FR", label: "French" },
//    { code: "es-ES", label: "Spanish" },
//    { code: "de-DE", label: "German" }
//  ];


//  langSelect.innerHTML = voices.map((v, i) => `<option value="${i}">${v.name} (${v.lang})</option>`).join("");
//  if (recognition) {
////    langSelect.addEventListener("change", () => { recognition.lang = langSelect.value; });
//    recognition.lang = languages[voiceSelect.value];
//    console.log(recognition.lang);
//  }
});

