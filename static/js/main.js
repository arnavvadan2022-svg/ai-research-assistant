// API Configuration
const API_BASE_URL = window.location.origin + '/api';

// State
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let isLogin = true;
let currentSessionId = localStorage.getItem('currentSessionId') || null;

// DOM Elements
const authContainer = document.getElementById('authContainer');
const appContainer = document.getElementById('appContainer');
const authForm = document.getElementById('authForm');
const authTitle = document.getElementById('authTitle');
const usernameGroup = document.getElementById('usernameGroup');
const authSwitchText = document.getElementById('authSwitchText');
const authSwitchLink = document.getElementById('authSwitchLink');
const welcomeSection = document.getElementById('welcomeSection');
const chatSection = document.getElementById('chatSection');
const chatMessages = document.getElementById('chatMessages');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const sessionsBtn = document.getElementById('sessionsBtn');
const logoutBtn = document.getElementById('logoutBtn');
const typingIndicator = document.getElementById('typingIndicator');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        showApp();
    } else {
        showAuth();
    }
    
    setupEventListeners();
});

function setupEventListeners() {
    // Auth
    authForm.addEventListener('submit', handleAuth);
    authSwitchLink.addEventListener('click', toggleAuthMode);
    
    // Chat
    sendBtn.addEventListener('click', sendQuestion);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendQuestion();
        }
    });
    
    // Auto-resize textarea
    questionInput.addEventListener('input', () => {
        questionInput.style.height = 'auto';
        questionInput.style.height = questionInput.scrollHeight + 'px';
    });
    
    // Navigation
    newChatBtn.addEventListener('click', startNewChat);
    sessionsBtn.addEventListener('click', showSessions);
    logoutBtn.addEventListener('click', logout);
    
    // Topic cards
    document.querySelectorAll('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const topic = card.getAttribute('data-topic');
            questionInput.value = topic;
            sendQuestion();
        });
    });
    
    // Modal close
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').style.display = 'none';
        });
    });
    
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

// Auth Functions
function toggleAuthMode(e) {
    e.preventDefault();
    isLogin = !isLogin;
    
    if (isLogin) {
        authTitle.textContent = 'Sign In';
        usernameGroup.style.display = 'none';
        authSwitchText.textContent = "Don't have an account?";
        authSwitchLink.textContent = 'Sign Up';
        authForm.querySelector('button[type="submit"]').textContent = 'Sign In';
    } else {
        authTitle.textContent = 'Sign Up';
        usernameGroup.style.display = 'block';
        authSwitchText.textContent = 'Already have an account?';
        authSwitchLink.textContent = 'Sign In';
        authForm.querySelector('button[type="submit"]').textContent = 'Sign Up';
    }
}

async function handleAuth(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const username = document.getElementById('username').value;
    
    const endpoint = isLogin ? '/login' : '/register';
    const data = isLogin 
        ? { email, password }
        : { username, email, password };
    
    try {
        const response = await fetch(API_BASE_URL + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            authToken = result.token;
            currentUser = result.user;
            localStorage.setItem('authToken', authToken);
            showApp();
            showNotification('Welcome! Ask me anything about quantum computing or quantum mechanics.', 'success');
        } else {
            showNotification(result.error || 'Authentication failed', 'error');
        }
    } catch (error) {
        showNotification('Network error. Please try again.', 'error');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    currentSessionId = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentSessionId');
    showAuth();
    showNotification('Logged out successfully', 'success');
}

function showAuth() {
    authContainer.style.display = 'flex';
    appContainer.style.display = 'none';
    logoutBtn.style.display = 'none';
    newChatBtn.style.display = 'none';
    sessionsBtn.style.display = 'none';
}

function showApp() {
    authContainer.style.display = 'none';
    appContainer.style.display = 'flex';
    logoutBtn.style.display = 'block';
    newChatBtn.style.display = 'block';
    sessionsBtn.style.display = 'block';
    
    // Show welcome or restore session
    if (currentSessionId) {
        loadSession(currentSessionId);
    } else {
        showWelcome();
    }
}

function showWelcome() {
    welcomeSection.style.display = 'block';
    chatSection.style.display = 'none';
}

function showChat() {
    welcomeSection.style.display = 'none';
    chatSection.style.display = 'flex';
}

// Chat Functions
async function sendQuestion() {
    const question = questionInput.value.trim();
    
    if (!question) return;
    
    // Add user message to UI
    addMessage('user', question);
    
    // Clear input
    questionInput.value = '';
    questionInput.style.height = 'auto';
    
    // Show chat section if hidden
    showChat();
    
    // Show typing indicator
    showTyping();
    
    try {
        const response = await fetch(API_BASE_URL + '/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                question: question,
                session_id: currentSessionId
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Update session ID
            currentSessionId = result.session_id;
            localStorage.setItem('currentSessionId', currentSessionId);
            
            // Hide typing indicator
            hideTyping();
            
            // Add assistant message
            addMessage('assistant', result.answer, result.sources);
            
            // Show suggestion if not quantum
            if (!result.is_quantum && result.suggested_topics) {
                showSuggestedTopics(result.suggested_topics);
            }
        } else {
            hideTyping();
            showNotification(result.error || 'Failed to get answer from the server. Please try again.', 'error');
        }
    } catch (error) {
        hideTyping();
        console.error('Chat error:', error);
        showNotification('Failed to connect to the server. Please check your internet connection and try again.', 'error');
    }
}

function addMessage(role, content, sources = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    // Add icon
    const iconDiv = document.createElement('div');
    iconDiv.className = 'message-icon';
    iconDiv.innerHTML = role === 'user' 
        ? '<i class="fas fa-user"></i>' 
        : '<i class="fas fa-atom"></i>';
    
    // Add content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format message with markdown-like rendering
    contentDiv.innerHTML = formatMessage(content);
    
    messageDiv.appendChild(iconDiv);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessage(text) {
    // Simple formatting for better readability
    let formatted = text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\[arXiv:(.*?)\]/g, '<span class="citation">[arXiv:$1]</span>')
        .replace(/\[Source: (.*?)\]/g, '<span class="citation">[Source: $1]</span>');
    
    // Make URLs clickable
    formatted = formatted.replace(
        /(https?:\/\/[^\s<]+)/g,
        '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    
    return formatted;
}

function showTyping() {
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

function startNewChat() {
    currentSessionId = null;
    localStorage.removeItem('currentSessionId');
    chatMessages.innerHTML = '';
    showWelcome();
    showNotification('Started new chat', 'success');
}

async function loadSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.messages) {
            chatMessages.innerHTML = '';
            showChat();
            
            result.messages.forEach(msg => {
                addMessage(msg.role, msg.content, msg.sources);
            });
        }
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

async function showSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displaySessionsList(result.sessions);
        }
    } catch (error) {
        showNotification('Error loading chat history', 'error');
    }
}

function displaySessionsList(sessions) {
    const sessionsList = document.getElementById('sessionsList');
    const modal = document.getElementById('sessionsModal');
    
    if (!sessions || sessions.length === 0) {
        sessionsList.innerHTML = '<p class="no-sessions">No chat history yet. Start a conversation!</p>';
    } else {
        sessionsList.innerHTML = sessions.map(session => {
            const date = new Date(session.created_at).toLocaleString();
            return `
                <div class="session-item" data-session-id="${session.id}">
                    <div class="session-info">
                        <i class="fas fa-comments"></i>
                        <div>
                            <div class="session-date">${date}</div>
                            <div class="session-messages">${session.message_count} messages</div>
                        </div>
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-sm load-session" data-session-id="${session.id}">
                            <i class="fas fa-folder-open"></i> Load
                        </button>
                        <button class="btn btn-sm btn-danger delete-session" data-session-id="${session.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add event listeners
        sessionsList.querySelectorAll('.load-session').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.closest('.load-session').dataset.sessionId;
                currentSessionId = sessionId;
                localStorage.setItem('currentSessionId', sessionId);
                loadSession(sessionId);
                modal.style.display = 'none';
            });
        });
        
        sessionsList.querySelectorAll('.delete-session').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const sessionId = e.target.closest('.delete-session').dataset.sessionId;
                if (confirm('Delete this chat session?')) {
                    await deleteSession(sessionId);
                    showSessions(); // Refresh list
                }
            });
        });
    }
    
    modal.style.display = 'block';
}

async function deleteSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            if (sessionId === currentSessionId) {
                startNewChat();
            }
            showNotification('Chat deleted', 'success');
        }
    } catch (error) {
        showNotification('Error deleting chat', 'error');
    }
}

function showSuggestedTopics(topics) {
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'suggested-topics-inline';
    suggestionsDiv.innerHTML = `
        <p><strong>💡 Try asking about these quantum topics:</strong></p>
        <ul>
            ${topics.slice(0, 4).map(topic => `<li>${topic}</li>`).join('')}
        </ul>
    `;
    chatMessages.appendChild(suggestionsDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Notification System
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
