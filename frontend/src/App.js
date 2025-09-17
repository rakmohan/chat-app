import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const generateUserId = () => {
  return 'user_' + Math.random().toString(36).substr(2, 9);
};

const generateUserName = () => {
  const adjectives = ['Cool', 'Smart', 'Happy', 'Brave', 'Kind', 'Swift'];
  const nouns = ['Tiger', 'Eagle', 'Wolf', 'Bear', 'Fox', 'Lion'];
  return adjectives[Math.floor(Math.random() * adjectives.length)] + 
         nouns[Math.floor(Math.random() * nouns.length)];
};

function App() {
  const [userId] = useState(() => generateUserId());
  const [userName] = useState(() => generateUserName());
  const [socket, setSocket] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState({});
  const [newMessage, setNewMessage] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  
  const messagesEndRef = useRef(null);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages, activeChat]);

  useEffect(() => {
    // Initialize WebSocket connection
    const ws = new WebSocket(`ws://localhost:8000/ws/${userId}?name=${userName}`);
    
    ws.onopen = () => {
      console.log('Connected to WebSocket');
      setConnectionStatus('connected');
      setSocket(ws);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received message:', data);
      
      switch (data.type) {
        case 'online_users':
          setOnlineUsers(data.users.filter(user => user.user_id !== userId));
          break;
          
        case 'chat_started':
          const chatId = data.chat_id;
          setActiveChat({
            id: chatId,
            participants: data.participants,
            otherUser: data.participants.find(p => p.user_id !== userId)
          });
          // Initialize messages array for this chat if it doesn't exist
          setMessages(prev => ({
            ...prev,
            [chatId]: prev[chatId] || []
          }));
          break;
          
        case 'chat_message':
          setMessages(prev => ({
            ...prev,
            [data.chat_id]: [
              ...(prev[data.chat_id] || []),
              {
                sender_id: data.sender_id,
                sender_name: data.sender_name,
                content: data.content,
                timestamp: data.timestamp
              }
            ]
          }));
          break;
          
        case 'chat_ended':
          setActiveChat(null);
          break;
          
        case 'user_left_chat':
          setActiveChat(null);
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    };
    
    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      setConnectionStatus('disconnected');
      setSocket(null);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('error');
    };
    
    return () => {
      ws.close();
    };
  }, [userId, userName]);

  const startChat = (targetUser) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'start_chat',
        target_user_id: targetUser.user_id
      }));
    }
  };

  const sendMessage = () => {
    if (newMessage.trim() && activeChat && socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'chat_message',
        chat_id: activeChat.id,
        content: newMessage.trim()
      }));
      setNewMessage('');
    }
  };

  const endChat = () => {
    if (activeChat && socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'end_chat',
        chat_id: activeChat.id
      }));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="app">
      <div className="header">
        <h1>Real-time Chat</h1>
        <div className="user-info">
          <span className="user-name">Welcome, {userName}!</span>
          <div className={`connection-status ${connectionStatus}`}>
            {connectionStatus === 'connected' && '🟢'}
            {connectionStatus === 'disconnected' && '🔴'}
            {connectionStatus === 'error' && '🟡'}
            {connectionStatus}
          </div>
        </div>
      </div>
      
      <div className="main-content">
        <div className="sidebar">
          <h3>Online Users ({onlineUsers.length})</h3>
          <div className="users-list">
            {onlineUsers.length === 0 ? (
              <div className="no-users">No other users online</div>
            ) : (
              onlineUsers.map(user => (
                <div 
                  key={user.user_id} 
                  className="user-item"
                  onClick={() => startChat(user)}
                >
                  <span className="user-indicator">👤</span>
                  <span className="user-name">{user.name}</span>
                  <button className="chat-btn">Chat</button>
                </div>
              ))
            )}
          </div>
        </div>
        
        <div className="chat-area">
          {!activeChat ? (
            <div className="no-chat">
              <h2>Select a user to start chatting</h2>
              <p>Click on any online user from the sidebar to begin a conversation.</p>
            </div>
          ) : (
            <>
              <div className="chat-header">
                <h3>Chat with {activeChat.otherUser.name}</h3>
                <button onClick={endChat} className="end-chat-btn">End Chat</button>
              </div>
              
              <div className="messages-container">
                <div className="messages">
                  {(messages[activeChat.id] || []).map((message, index) => (
                    <div 
                      key={index} 
                      className={`message ${message.sender_id === userId ? 'own' : 'other'}`}
                    >
                      <div className="message-content">
                        <div className="message-text">{message.content}</div>
                        <div className="message-time">
                          {formatTimestamp(message.timestamp)}
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              </div>
              
              <div className="message-input-container">
                <div className="message-input">
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type a message..."
                    rows="1"
                  />
                  <button onClick={sendMessage} disabled={!newMessage.trim()}>
                    Send
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
