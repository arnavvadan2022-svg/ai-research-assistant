// API Configuration
const API_BASE_URL = window.location.origin + '/api';

// State
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let isLogin = true;

// DOM Elements
const authContainer = document.getElementById('authContainer');
const appContainer = document.getElementById('appContainer');
const authForm = document.getElementById('authForm');
const authTitle = document.getElementById('authTitle');
const usernameGroup = document.getElementById('usernameGroup');
const authSwitchText = document.getElementById('authSwitchText');
const authSwitchLink = document.getElementById('authSwitchLink');
const searchBtn = document.getElementById('searchBtn');
const searchInput = document.getElementById('searchInput');
const maxResults = document.getElementById('maxResults');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const resultsGrid = document.getElementById('resultsGrid');
const resultsCount = document.getElementById('resultsCount');
const logoutBtn = document.getElementById('logoutBtn');
const savedPapersBtn = document.getElementById('savedPapersBtn');
const historyBtn = document.getElementById('historyBtn');

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
    authForm.addEventListener('submit', handleAuth);
    authSwitchLink.addEventListener('click', toggleAuthMode);
    searchBtn.addEventListener('click', searchPapers);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchPapers();
    });
    logoutBtn.addEventListener('click', logout);
    savedPapersBtn.addEventListener('click', showSavedPapers);
    historyBtn.addEventListener('click', showHistory);
    
    // Modal close buttons
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').style.display = 'none';
        });
    });
    
    // Close modal on outside click
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
        } else {
            alert(result.error || 'Authentication failed');
        }
    } catch (error) {
        console.error('Auth error:', error);
        alert('An error occurred. Please try again.');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showAuth();
}

function showAuth() {
    authContainer.style.display = 'flex';
    appContainer.style.display = 'none';
    logoutBtn.style.display = 'none';
}

function showApp() {
    authContainer.style.display = 'none';
    appContainer.style.display = 'block';
    logoutBtn.style.display = 'inline-flex';
}

// Search Functions
async function searchPapers() {
    const query = searchInput.value.trim();
    if (!query) {
        alert('Please enter a search query');
        return;
    }
    
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    
    try {
        const response = await fetch(API_BASE_URL + '/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                query: query,
                max_results: parseInt(maxResults.value)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayResults(result.results, result.count);
        } else {
            alert(result.error || 'Search failed');
        }
    } catch (error) {
        console.error('Search error:', error);
        alert('An error occurred during search');
    } finally {
        loading.style.display = 'none';
    }
}

function displayResults(papers, count) {
    resultsCount.textContent = `${count} papers found`;
    resultsGrid.innerHTML = '';
    
    if (papers.length === 0) {
        resultsGrid.innerHTML = '<p class="text-center text-muted">No papers found</p>';
    } else {
        papers.forEach(paper => {
            const card = createPaperCard(paper);
            resultsGrid.appendChild(card);
        });
    }
    
    resultsSection.style.display = 'block';
}

function createPaperCard(paper) {
    const card = document.createElement('div');
    card.className = 'paper-card';
    
    const authorsText = paper.authors.slice(0, 3).join(', ') + 
        (paper.authors.length > 3 ? ' et al.' : '');
    
    const abstractPreview = paper.abstract.length > 300 
        ? paper.abstract.substring(0, 300) + '...'
        : paper.abstract;
    
    card.innerHTML = `
        <h3>${paper.title}</h3>
        <div class="paper-authors">${authorsText}</div>
        <p class="paper-abstract">${abstractPreview}</p>
        <div class="paper-meta">
            <span class="paper-date">
                <i class="fas fa-calendar"></i> ${new Date(paper.published).toLocaleDateString()}
            </span>
            ${paper.categories ? `
                <span class="paper-categories">
                    <i class="fas fa-tags"></i> ${paper.categories.slice(0, 2).join(', ')}
                </span>
            ` : ''}
        </div>
        <div class="paper-actions">
            <button class="btn btn-primary btn-sm view-btn" data-paper='${JSON.stringify(paper).replace(/'/g, "&apos;")}'>
                <i class="fas fa-eye"></i> View Details
            </button>
            <button class="btn btn-secondary btn-sm summarize-btn" data-abstract="${escapeHtml(paper.abstract)}" data-id="${paper.id}">
                <i class="fas fa-magic"></i> Summarize
            </button>
            <button class="btn btn-success btn-sm save-btn" data-paper='${JSON.stringify(paper).replace(/'/g, "&apos;")}'>
                <i class="fas fa-bookmark"></i> Save
            </button>
            <a href="${paper.pdf_url}" target="_blank" class="btn btn-secondary btn-sm">
                <i class="fas fa-file-pdf"></i> PDF
            </a>
        </div>
    `;

    // Add event listeners to buttons
    const summarizeBtn = card.querySelector('.summarize-btn');
    summarizeBtn.addEventListener('click', function() {
        const abstract = this.getAttribute('data-abstract');
        const paperId = this.getAttribute('data-id');
        summarizePaper(paperId, abstract);
    });

    const viewBtn = card.querySelector('.view-btn');
    viewBtn.addEventListener('click', function() {
        const paperData = JSON.parse(this.getAttribute('data-paper'));
        viewPaper(paperData);
    });

    const saveBtn = card.querySelector('.save-btn');
    saveBtn.addEventListener('click', function() {
        const paperData = JSON.parse(this.getAttribute('data-paper'));
        savePaperToLibrary(paperData);
    });

    return card;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function summarizePaper(paperId, abstract) {
    // Show loading state
    const btn = event.target.closest('.summarize-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Summarizing...';
    btn.disabled = true;

    try {
        const response = await fetch(API_BASE_URL + '/summarize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                text: abstract,
                paper_id: paperId
            })
        });

        const result = await response.json();

        if (response.ok) {
            // Show summary in a nice modal or alert
            showSummaryModal(result.summary);
        } else {
            alert('Failed to generate summary: ' + result.error);
        }
    } catch (error) {
        console.error('Summarization error:', error);
        alert('An error occurred while generating summary');
    } finally {
        // Restore button state
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function showSummaryModal(summary) {
    // Create a nice modal for the summary
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>📄 Paper Summary</h2>
            <div style="white-space: pre-wrap; line-height: 1.8; margin-top: 1rem;">
                ${summary}
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close modal handlers
    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

async function savePaperToLibrary(paper) {
    const btn = event.target.closest('.save-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    try {
        const response = await fetch(API_BASE_URL + '/papers/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                paper_id: paper.id,
                title: paper.title,
                authors: paper.authors,
                abstract: paper.abstract,
                url: paper.url,
                published_date: paper.published
            })
        });

        const result = await response.json();

        if (response.ok) {
            btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
            btn.classList.remove('btn-success');
            btn.classList.add('btn-primary');
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-success');
                btn.disabled = false;
            }, 2000);

            // Show success message
            showNotification('Paper saved to your library! ✅', 'success');
        } else {
            alert('Failed to save paper: ' + result.error);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (error) {
        console.error('Save paper error:', error);
        alert('An error occurred while saving the paper');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

function viewPaper(paper) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';

    const authorsText = paper.authors.join(', ');
    const categoriesText = paper.categories ? paper.categories.join(', ') : 'N/A';

    modal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>${paper.title}</h2>
            <p><strong>Authors:</strong> ${authorsText}</p>
            <p><strong>Published:</strong> ${new Date(paper.published).toLocaleDateString()}</p>
            <p><strong>Categories:</strong> ${categoriesText}</p>
            <p><strong>arXiv ID:</strong> ${paper.id}</p>
            <h3>Abstract</h3>
            <p style="line-height: 1.6;">${paper.abstract}</p>
            <div style="margin-top: 1rem;">
                <a href="${paper.url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> View on arXiv
                </a>
                <a href="${paper.pdf_url}" target="_blank" class="btn btn-secondary">
                    <i class="fas fa-file-pdf"></i> Download PDF
                </a>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

async function showSavedPapers() {
    const modal = document.getElementById('savedPapersModal');
    const list = document.getElementById('savedPapersList');

    try {
        const response = await fetch(API_BASE_URL + '/papers', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const result = await response.json();

        if (response.ok) {
            list.innerHTML = '';
            if (result.papers.length === 0) {
                list.innerHTML = '<p class="text-center text-muted">No saved papers yet. Save papers from your search results!</p>';
            } else {
                result.papers.forEach(paper => {
                    const item = document.createElement('div');
                    item.className = 'paper-card';

                    // Parse authors if it's JSON string
                    let authorsList = [];
                    try {
                        authorsList = typeof paper.authors === 'string' ? JSON.parse(paper.authors) : paper.authors;
                    } catch (e) {
                        authorsList = [];
                    }
                    const authorsText = authorsList.length > 0 ? authorsList.slice(0, 3).join(', ') : 'Unknown';

                    item.innerHTML = `
                        <h3>${paper.title}</h3>
                        <p class="paper-authors">${authorsText}</p>
                        <p class="text-muted"><i class="fas fa-bookmark"></i> Saved on ${new Date(paper.saved_at).toLocaleDateString()}</p>
                        ${paper.summary ? `<p><strong>Summary:</strong> ${paper.summary}</p>` : ''}
                        <div class="paper-actions">
                            <a href="${paper.url}" target="_blank" class="btn btn-primary btn-sm">
                                <i class="fas fa-external-link-alt"></i> View on arXiv
                            </a>
                            <button class="btn btn-danger btn-sm delete-paper-btn" data-id="${paper.id}">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    `;

                    const deleteBtn = item.querySelector('.delete-paper-btn');
                    deleteBtn.addEventListener('click', function() {
                        deletePaper(this.getAttribute('data-id'));
                    });

                    list.appendChild(item);
                });
            }
            modal.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading saved papers:', error);
        alert('Failed to load saved papers');
    }
}

async function showHistory() {
    const modal = document.getElementById('historyModal');
    const list = document.getElementById('historyList');

    try {
        const response = await fetch(API_BASE_URL + '/history', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        const result = await response.json();

        if (response.ok) {
            list.innerHTML = '';
            if (result.history.length === 0) {
                list.innerHTML = '<p class="text-center text-muted">No search history</p>';
            } else {
                result.history.forEach(query => {
                    const item = document.createElement('div');
                    item.className = 'paper-card';
                    item.innerHTML = `
                        <p><strong>${query.query_text}</strong></p>
                        <p class="text-muted">${new Date(query.created_at).toLocaleString()}</p>
                        <button class="btn btn-secondary btn-sm search-again-btn" data-query="${escapeHtml(query.query_text)}">
                            <i class="fas fa-search"></i> Search Again
                        </button>
                    `;

                    const searchBtn = item.querySelector('.search-again-btn');
                    searchBtn.addEventListener('click', function() {
                        searchFromHistory(this.getAttribute('data-query'));
                    });

                    list.appendChild(item);
                });
            }
            modal.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        alert('Failed to load search history');
    }
}

function searchFromHistory(query) {
    document.getElementById('historyModal').style.display = 'none';
    searchInput.value = query;
    searchPapers();
}

async function deletePaper(paperId) {
    if (!confirm('Are you sure you want to delete this paper?')) return;

    try {
        const response = await fetch(API_BASE_URL + `/papers/${paperId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            showNotification('Paper deleted successfully! 🗑️', 'success');
            showSavedPapers(); // Refresh the list
        } else {
            alert('Failed to delete paper');
        }
    } catch (error) {
        console.error('Error deleting paper:', error);
        alert('Failed to delete paper');
    }
}

// Add CSS animation for notification
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);