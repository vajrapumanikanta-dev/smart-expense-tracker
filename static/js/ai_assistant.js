/**
 * SMART EXPENSE TRACKER - AI ASSISTANT CHAT INTERFACE
 */

document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatMessagesContainer');
    const chatInput = document.getElementById('chatInputMessage');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const suggestionPills = document.querySelectorAll('.prompt-pill');

    if (!chatContainer || !chatInput || !chatSendBtn) return;

    function formatMarkdown(text) {
        if (!text) return '';
        let formatted = text
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Bullet points
            .replace(/^• (.*?)$/gm, '<li style="margin-left: 20px; list-style-type: disc;">$1</li>')
            // Line breaks
            .replace(/\n/g, '<br>');
        return formatted;
    }

    function appendMessage(sender, text, data = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-msg ${sender}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = `chat-avatar ${sender}`;
        avatarDiv.innerHTML = sender === 'ai' 
            ? '<i class="fa-solid fa-wand-magic-sparkles"></i>' 
            : '<i class="fa-solid fa-user"></i>';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'chat-bubble';
        bubbleDiv.innerHTML = formatMarkdown(text);

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(bubbleDiv);
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function sendMessage(messageText) {
        const text = messageText || chatInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatInput.value = '';
        chatSendBtn.disabled = true;

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-msg ai';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="chat-avatar ai"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
            <div class="chat-bubble"><i class="fa-solid fa-ellipsis fa-fade"></i> AI is thinking...</div>
        `;
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const res = await fetch('/ai/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            // Remove typing indicator
            const typingEl = document.getElementById('typingIndicator');
            if (typingEl) typingEl.remove();

            if (res.ok) {
                appendMessage('ai', data.answer, data.data);
            } else {
                appendMessage('ai', 'I encountered an issue processing your request: ' + (data.error || 'Unknown error'));
            }
        } catch (err) {
            const typingEl = document.getElementById('typingIndicator');
            if (typingEl) typingEl.remove();
            appendMessage('ai', 'Sorry, I am unable to connect to the financial intelligence service right now.');
        } finally {
            chatSendBtn.disabled = false;
        }
    }

    chatSendBtn.addEventListener('click', () => sendMessage());

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    suggestionPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const prompt = pill.getAttribute('data-prompt');
            if (prompt) {
                sendMessage(prompt);
            }
        });
    });
});
