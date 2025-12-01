# 🏢 AI Corporate Intelligence Hub

A modern, AI-powered corporate assistant built with FastAPI and the Model Context Protocol (MCP). Features real-time chat with streaming responses, RAG-based document search, database management, web search capabilities, and voice interaction.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)
![Mistral AI](https://img.shields.io/badge/LLM-Mistral%20AI-orange.svg)

---

## ✨ Features

### 🤖 AI Assistant
- **Streaming Chat** - Real-time responses with Server-Sent Events (SSE)
- **Context-Aware** - Knows current user, datetime, and system context
- **Markdown Support** - Rich formatting with code highlighting
- **Conversation History** - Persistent chat history per user

### 🔧 MCP Tools Integration
- **Database CRUD** - Manage employees, projects, tasks, documents
- **RAG Document Search** - Query uploaded documents (PDF, TXT, etc.)
- **Web Search** - DuckDuckGo integration for real-time information
- **News Search** - Search recent news articles
- **Email Integration** - Send emails via SMTP
- **File Operations** - Search and open files
- **Reminders** - Schedule task reminders

### 🔐 Authentication & Access Control
- **JWT Authentication** - Secure token-based auth
- **Role-Based Access** - 3 access levels (Read-Only, Write, Admin)
- **User Registration** - Self-service account creation
- **Session Management** - Persistent login sessions

### 🎨 Modern UI/UX
- **Responsive Design** - Mobile-friendly with hamburger menu
- **Dark Theme** - Eye-friendly corporate design
- **SVG Logo** - Custom animated logo
- **Toast Notifications** - Visual feedback for actions

### 🔊 Voice Features
- **Speech Recognition** - Voice input with Web Speech API
- **Text-to-Speech** - Read responses aloud with voice selection
- **Voice Persistence** - Remember preferred voice
- **Audio Feedback** - Sound cues for mic/speech actions
- **Visual Indicators** - Pulsing animations for active states

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- Mistral AI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AI-Corporate-Intelligence-Hub.git
   cd AI-Corporate-Intelligence-Hub
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install fastmcp duckduckgo-search chromadb sentence-transformers
   ```

4. **Configure environment**
   
   Create a `.env` file in the root directory:
   ```env
   # Required
   MISTRAL_API_KEY=your_mistral_api_key_here
   SECRET_KEY=your_jwt_secret_key_here
   
   # Optional - Email (for send_email tool)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASS=your_app_password
   ```

5. **Initialize database**
   ```bash
   python db_init.py
   ```

### Running the Application

You need to run **two servers** in separate terminals:

**Terminal 1 - MCP Server (Tools)**
```bash
python mcp_server.py
```
> Runs on `http://localhost:4000`

**Terminal 2 - Main Application**
```bash
python main.py
```
> Runs on `http://localhost:8080`

Open your browser and navigate to: **http://localhost:8080**

---

## 📁 Project Structure

```
AI-Corporate-Intelligence-Hub/
├── 📄 main.py              # FastAPI application & chat endpoints
├── 📄 mcp_server.py        # MCP tools server (FastMCP)
├── 📄 mcp_client.py        # MCP client for tool integration
├── 📄 config.py            # Configuration settings
├── 📄 models.py            # SQLModel database models
├── 📄 db.py                # Database connection
├── 📄 db_init.py           # Database initialization script
├── 📄 auth.py              # JWT authentication logic
├── 📄 llm_manager.py       # LLM interaction (Mistral AI)
├── 📄 rag_manager.py       # RAG with ChromaDB
├── 📄 requirements.txt     # Python dependencies
├── 📄 .env                 # Environment variables (create this)
├── 📂 templates/
│   ├── index.html          # Main chat interface
│   ├── login.html          # Login page
│   └── register.html       # Registration page
├── 📂 static/
│   ├── script.js           # Frontend JavaScript
│   ├── styles.css          # CSS styling
│   └── logo.svg            # App logo
└── 📂 uploads/             # Uploaded documents storage
```

---

## 🔧 Available MCP Tools

### Database Operations
| Tool | Description | Access Level |
|------|-------------|--------------|
| `create_employee` | Create new employee | Admin |
| `get_employee` | Get employee by email/id | Read |
| `list_employees` | List all employees | Read |
| `delete_employee` | Delete employee | Admin |
| `create_project` | Create new project | Write |
| `get_project` | Get project by id | Read |
| `list_projects` | List all projects | Read |
| `delete_project` | Delete project | Admin |
| `create_task` | Create new task | Write |
| `get_task` | Get task by id | Read |
| `list_tasks` | List all tasks | Read |
| `update_task_status` | Update task status | Write |
| `delete_task` | Delete task | Admin |
| `get_document` | Get document by id | Read |
| `list_documents` | List all documents | Read |

### RAG & Document Search
| Tool | Description |
|------|-------------|
| `search_documents` | Search uploaded documents |
| `list_uploaded_documents` | List all uploaded files |
| `clear_uploaded_documents` | Clear all documents (Admin) |

### Web & External
| Tool | Description |
|------|-------------|
| `web_search` | Search the internet |
| `web_search_news` | Search recent news |
| `open_browser_search` | Open browser with search |
| `send_simple_email` | Send email via SMTP |

### Utilities
| Tool | Description |
|------|-------------|
| `launch_application` | Launch system app |
| `search_and_open_file` | Find and open files |
| `set_reminder` | Schedule a reminder |
| `health_check` | Check server status |
| `get_current_user` | Get logged-in user info |
| `get_my_access_level` | Check user permissions |

---

## 🛡️ Access Levels

| Level | Name | Permissions |
|-------|------|-------------|
| 1 | Read-Only | View data, search documents, web search |
| 2 | Write | All Read + Create/update projects, tasks |
| 3 | Admin | All Write + Create/delete employees, manage system |

---

## 🎤 Voice Commands

The application supports voice interaction:
- **Click the microphone** 🎤 to start voice input
- **Click the speaker** 🔊 on any message to read it aloud
- **Voice settings** - Select preferred voice in the header
- **Mute/Unmute** - Control text-to-speech output

---

## 📤 Document Upload

Upload documents for RAG-based querying:
1. Click the **upload button** in the chat interface
2. Select PDF, TXT, or other text documents
3. Documents are chunked and embedded in ChromaDB
4. Ask questions about document content

---

## 🔍 Web Search

The AI can search the web for:
- Current events and news
- Facts and information
- Topics not in local documents

Simply ask naturally: *"Search the web for latest AI news"*

---

## 🛠️ Technologies

| Category | Technology |
|----------|------------|
| **Backend** | FastAPI, Uvicorn |
| **LLM** | Mistral AI |
| **Database** | SQLite, SQLModel, SQLAlchemy |
| **Vector Store** | ChromaDB, Sentence Transformers |
| **MCP** | FastMCP, langchain-mcp-adapters |
| **Web Search** | duckduckgo-search |
| **Auth** | python-jose (JWT), passlib |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Voice** | Web Speech API |
| **Markdown** | marked.js |

---

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/login` | GET/POST | User login |
| `/register` | GET/POST | User registration |
| `/logout` | GET | Logout user |
| `/chat` | POST | Send chat message (SSE) |
| `/upload` | POST | Upload document |
| `/conversations` | GET | List user conversations |
| `/conversations/{id}` | GET | Get conversation messages |
| `/conversations/{id}` | DELETE | Delete conversation |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**KINIMO Paul-David Ephraïm**

ISP Final Project - AI Corporate Intelligence Hub

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Mistral AI](https://mistral.ai/) - Large language model
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool integration
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [DuckDuckGo](https://duckduckgo.com/) - Web search API
