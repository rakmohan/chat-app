from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import uuid
from typing import Dict, Set
import asyncpg
import os
from datetime import datetime

app = FastAPI()

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active connections and chat sessions
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_names: Dict[str, str] = {}
        self.chat_sessions: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_name: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_names[user_id] = user_name
        
        # Add user to database
        await self.add_user_to_db(user_id, user_name)
        
        # Broadcast updated user list
        await self.broadcast_user_list()
        
    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_names:
            del self.user_names[user_id]
            
        # Remove user from database
        await self.remove_user_from_db(user_id)
        
        # Remove user from any active chat sessions
        sessions_to_remove = []
        for chat_id, participants in self.chat_sessions.items():
            if user_id in participants:
                participants.discard(user_id)
                # Notify other participant that user left
                for other_user in participants:
                    if other_user in self.active_connections:
                        await self.active_connections[other_user].send_text(json.dumps({
                            "type": "user_left_chat",
                            "chat_id": chat_id,
                            "user_id": user_id
                        }))
                if len(participants) <= 1:
                    sessions_to_remove.append(chat_id)
        
        # Clean up empty sessions
        for chat_id in sessions_to_remove:
            del self.chat_sessions[chat_id]
            
        # Broadcast updated user list
        await self.broadcast_user_list()
    
    async def broadcast_user_list(self):
        online_users = [
            {"user_id": user_id, "name": name} 
            for user_id, name in self.user_names.items()
        ]
        message = json.dumps({
            "type": "online_users",
            "users": online_users
        })
        
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except:
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            await self.disconnect(user_id)
    
    async def send_message_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                return True
            except:
                await self.disconnect(user_id)
                return False
        return False
    
    def create_chat_session(self, user1_id: str, user2_id: str) -> str:
        # Create deterministic chat_id based on user IDs
        chat_id = "-".join(sorted([user1_id, user2_id]))
        self.chat_sessions[chat_id] = {user1_id, user2_id}
        return chat_id
    
    def get_chat_participants(self, chat_id: str) -> Set[str]:
        return self.chat_sessions.get(chat_id, set())
    
    async def add_user_to_db(self, user_id: str, user_name: str):
        try:
            conn = await get_db_connection()
            await conn.execute(
                "INSERT INTO chat_users (user_id, name, connected_at) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET connected_at = $3",
                user_id, user_name, datetime.utcnow()
            )
            await conn.close()
        except Exception as e:
            print(f"Database error: {e}")
    
    async def remove_user_from_db(self, user_id: str):
        try:
            conn = await get_db_connection()
            await conn.execute("DELETE FROM chat_users WHERE user_id = $1", user_id)
            await conn.close()
        except Exception as e:
            print(f"Database error: {e}")

manager = ConnectionManager()

# Database connection
async def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL", default=None)
    return await asyncpg.connect(DATABASE_URL)

# Initialize database
async def init_db():
    try:
        conn = await get_db_connection()
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_users (
                user_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Clear existing users on startup
        await conn.execute("DELETE FROM chat_users")
        await conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    # Get user name from query params or assign default
    user_name = websocket.query_params.get("name", f"User_{user_id[:8]}")
    
    await manager.connect(websocket, user_id, user_name)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "start_chat":
                target_user_id = message.get("target_user_id")
                if target_user_id in manager.active_connections:
                    chat_id = manager.create_chat_session(user_id, target_user_id)
                    
                    # Notify both users about the chat session
                    chat_start_message = {
                        "type": "chat_started",
                        "chat_id": chat_id,
                        "participants": [
                            {"user_id": user_id, "name": manager.user_names[user_id]},
                            {"user_id": target_user_id, "name": manager.user_names[target_user_id]}
                        ]
                    }
                    
                    await manager.send_message_to_user(user_id, chat_start_message)
                    await manager.send_message_to_user(target_user_id, chat_start_message)
            
            elif message_type == "chat_message":
                chat_id = message.get("chat_id")
                content = message.get("content")
                timestamp = datetime.utcnow().isoformat()
                
                participants = manager.get_chat_participants(chat_id)
                
                chat_message = {
                    "type": "chat_message",
                    "chat_id": chat_id,
                    "sender_id": user_id,
                    "sender_name": manager.user_names[user_id],
                    "content": content,
                    "timestamp": timestamp
                }
                
                # Send message to all participants
                for participant_id in participants:
                    await manager.send_message_to_user(participant_id, chat_message)
            
            elif message_type == "end_chat":
                chat_id = message.get("chat_id")
                participants = manager.get_chat_participants(chat_id)
                
                # Notify all participants that chat ended
                for participant_id in participants:
                    await manager.send_message_to_user(participant_id, {
                        "type": "chat_ended",
                        "chat_id": chat_id,
                        "ended_by": user_id
                    })
                
                # Remove chat session
                if chat_id in manager.chat_sessions:
                    del manager.chat_sessions[chat_id]
    
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(user_id)

@app.get("/")
async def root():
    return {"message": "Real-time Chat API is running"}

@app.get("/online-users")
async def get_online_users():
    online_users = [
        {"user_id": user_id, "name": name} 
        for user_id, name in manager.user_names.items()
    ]
    return {"users": online_users}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
