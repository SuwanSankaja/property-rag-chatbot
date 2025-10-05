const API_ENDPOINT = CONFIG.API_ENDPOINT;
let userId = localStorage.getItem('propertyUserId');
if (!userId) {
    userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('propertyUserId', userId);
}

let conversationHistory = [];
let isProcessing = false;
let queryCount = 0;

const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

function scrollToBottom() {
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !isProcessing) {
        sendMessage();
    }
}

function sendSuggestion(text) {
    userInput.value = text;
    sendMessage();
}

function addMessage(content, isUser = false) {
    const welcomeMsg = chatContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = isUser ? 'You' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    scrollToBottom();
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(indicator);
    chatContainer.appendChild(typingDiv);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function formatPropertyCards(properties) {
    if (!properties || properties.length === 0) return '';
    
    let html = '<div style="margin-top: 16px;">';
    properties.forEach((prop, idx) => {
        const price = (prop.asking_price || 0).toLocaleString();
        const statusClass = prop.for_sale ? 'for-sale' : '';
        const statusText = prop.for_sale ? 'For Sale' : (prop.for_rent ? 'For Rent' : 'N/A');
        
        html += `
            <div class="property-card">
                <h4>${prop.property_name || 'Property ' + (idx + 1)}</h4>
                <p><strong>📍 Location:</strong> ${prop.community_name || ''}, ${prop.city_name || ''}</p>
                <p><strong>🏠 Type:</strong> ${prop.property_type || 'N/A'} | <strong>🛏️</strong> ${prop.number_of_bedrooms || 0} bed | <strong>🚿</strong> ${prop.bathrooms_total || 0} bath</p>
                <p><strong>📏 Area:</strong> ${prop.total_area_sqm || 'N/A'} sqm</p>
                <p class="price">${prop.asking_price_currency || 'AED'} ${price}</p>
                <span class="status-badge ${statusClass}">${statusText}</span>
                ${prop.listing_url ? `<br><a href="${prop.listing_url}" target="_blank">View Details →</a>` : ''}
            </div>
        `;
    });
    html += '</div>';
    return html;
}

async function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message || isProcessing) return;

    // Handle greetings
    const greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon'];
    if (greetings.some(g => message.toLowerCase() === g)) {
        addMessage(message, true);
        setTimeout(() => {
            addMessage("Hello! I'm your property search assistant. I can help you find apartments, villas, and other properties in Dubai. Try asking me things like:<br><br>• Show me 1 bedroom apartments<br>• Properties under 100,000 AED<br>• Luxury apartments in Dubai<br><br>What are you looking for?");
        }, 500);
        userInput.value = '';
        return;
    }

    isProcessing = true;
    sendBtn.disabled = true;
    userInput.disabled = true;

    addMessage(message, true);
    conversationHistory.push({
        role: 'user',
        content: message
    });

    userInput.value = '';
    showTypingIndicator();
    queryCount++;
    document.getElementById('queryCount').textContent = queryCount;

    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                query: message,
                conversation_history: conversationHistory,
                filters: {}
            })
        });

        removeTypingIndicator();

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        let responseContent;

        // Check if it's a count query
        if (data.is_count_query) {
            responseContent = data.response;
        } else if (data.properties && data.properties.length > 0) {
            responseContent = `Found <strong>${data.properties_found} properties</strong> matching your search!`;
            responseContent += formatPropertyCards(data.properties);
        } else {
            responseContent = "Sorry, I couldn't find any properties matching your criteria. Try adjusting your search!";
        }

        addMessage(responseContent);
        conversationHistory.push({
            role: 'assistant',
            content: data.response || responseContent
        });

        if (data.intent) {
            console.log('User Intent:', data.intent);
        }

    } catch (error) {
        removeTypingIndicator();
        console.error('Error:', error);
        addMessage('<div style="color: #ef4444;">Sorry, I encountered an error. Please try again.</div>');
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        userInput.disabled = false;
        userInput.focus();
    }
}

window.addEventListener('load', () => {
    userInput.focus();
});