
# chat-app

A simple real-time chat application built with **FastAPI (backend)**, **React (frontend)**, and **PostgreSQL**.

## Setup

### Database Setup:

#### Local Setup 

```bash   # Create PostgreSQL database
   sudo -u postgres psql
   CREATE DATABASE <db name>;
   CREATE USER <db user>> WITH PASSWORD '<your password>';
   GRANT ALL PRIVILEGES ON DATABASE <db name> TO <db user>;
```

#### Host it on AIVEN

You will get a SERVICE_URI as following:
postgres://USER:PASSWORD@SERVER:PORT/DB?sslmode=require

#### Setup environment variable

```bash
export DATABASE_URL=postgres://USER:PASSWORD@SERVER:PORT/DB?sslmode=require
```

### Backend Setup

```bash   
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py init

# Start backend server (http://localhost:8000)
python main.py
```

### Frontend Setup

```bash   
cd frontend

# Create React app
npx create-react-app .

# Replace App.js, App.css, package.json with provided files
npm install

# Start frontend server (http://localhost:3000)
npm start
```


# Testing

1. Open multiple browser tabs to http://localhost:3000
2. Each gets a unique user name.
3. Click any online user to start chatting.



# Architecture Highlights

* WebSocket Manager: Handles all connections, user tracking, and message routing
* Chat Sessions: Dynamic creation of 1-to-1 chat rooms
* Real-time Updates: Instant user list updates when users join/leave
* Memory-based Storage: Chat messages stored in memory (session-only)
* Database: Only used for online user tracking, not message history


# Tech Stack

* Backend → Python, FastAPI, WebSockets
* Frontend → React, WebSocket client
* Database → PostgreSQL (Aiven-hosted or local)


# API Endpoints

- `GET /`: Health check
- `GET /online-users`: Get list of online users
- `WebSocket /ws/{user_id}?name={user_name}`: WebSocket connection for real-time communication


# WebSocket Message Types

### Client to Server:

- `start_chat`: Initiate chat with another user
- `chat_message`: Send message in active chat
- `end_chat`: End current chat session

### Server to Client:

- `online_users`: Updated list of online users
- `chat_started`: Chat session initiated
- `chat_message`: New message received
- `chat_ended`: Chat session ended
- `user_left_chat`: Other user left the chat


# Notes

* Messages are not persisted in the database (only session-based).
* PostgreSQL is used only for tracking online users.