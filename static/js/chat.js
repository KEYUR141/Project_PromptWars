/**
 * VenueIQ — chat.js
 * Attendee AI chat interface — handles message sending, history, and typing indicators.
 */

'use strict';

let chatHistory = [];

/** Append a message bubble to the chat window */
function appendMessage(text, role) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  div.setAttribute('role', 'article');
  div.setAttribute('aria-label', role === 'user' ? 'Your message' : 'VenueIQ response');
  // Preserve line breaks from AI response
  div.innerHTML = text.replace(/\n/g, '<br/>');
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

/** Show animated typing indicator */
function showTyping() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'msg msg-typing';
  el.id = 'typing-indicator';
  el.setAttribute('aria-label', 'VenueIQ is thinking…');
  el.innerHTML = '<div class="dots"><span></span><span></span><span></span></div>';
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

/** Remove typing indicator */
function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}

/** Send a chat message to the AI */
async function sendChat() {
  const input = document.getElementById('chat-input');
  const btn   = document.getElementById('btn-send');
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;

  // UI: disable input, show user message
  input.value = '';
  input.disabled = true;
  if (btn) btn.disabled = true;

  appendMessage(message, 'user');
  showTyping();

  try {
    const data = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history: chatHistory }),
    });

    hideTyping();

    if (data.success) {
      appendMessage(data.reply, 'ai');
      // Maintain rolling history for context
      chatHistory.push({ role: 'user', parts: message });
      chatHistory.push({ role: 'model', parts: data.reply });
      if (chatHistory.length > 12) chatHistory = chatHistory.slice(-12);
    } else {
      appendMessage('⚠️ Sorry, I couldn\'t process that. Please try again.', 'ai');
    }
  } catch (err) {
    hideTyping();
    appendMessage(`⚠️ ${err.message}`, 'ai');
  } finally {
    input.disabled = false;
    if (btn) btn.disabled = false;
    input.focus();
  }
}

/** Fill input with a quick prompt and send */
function quickAsk(prompt) {
  const input = document.getElementById('chat-input');
  if (input) input.value = prompt;
  sendChat();
}

/** Clear chat history and reset UI */
function clearChat() {
  chatHistory = [];
  const container = document.getElementById('chat-messages');
  if (container) {
    container.innerHTML = `
      <div class="msg msg-ai" role="article" aria-label="VenueIQ greeting">
        👋 Chat cleared! Ask me anything about the event.
      </div>`;
  }
}
