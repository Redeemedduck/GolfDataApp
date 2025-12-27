"""
Simple Web Interface for Golf Coach AI

Run this file to start a local web server with a chat interface.
Access at: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from vertex_ai_agent import create_golf_coach
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Create global coach instance
coach = create_golf_coach()

@app.route('/')
def index():
    """Serve the main chat interface"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>🏌️ Golf Coach AI</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 800px;
            height: 90vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }

        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }

        .header p {
            font-size: 14px;
            opacity: 0.9;
        }

        .quick-questions {
            padding: 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            overflow-x: auto;
            white-space: nowrap;
        }

        .quick-questions button {
            display: inline-block;
            margin: 5px;
            padding: 8px 15px;
            background: white;
            border: 2px solid #667eea;
            border-radius: 20px;
            color: #667eea;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }

        .quick-questions button:hover {
            background: #667eea;
            color: white;
        }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }

        .message {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.5;
            white-space: pre-wrap;
        }

        .message.user .message-content {
            background: #667eea;
            color: white;
        }

        .message.coach .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
        }

        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }

        .message.user .avatar {
            background: #764ba2;
        }

        .message.coach .avatar {
            background: #4CAF50;
        }

        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }

        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }

        #messageInput:focus {
            border-color: #667eea;
        }

        #sendButton {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 15px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        #sendButton:hover {
            transform: scale(1.05);
        }

        #sendButton:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .typing-indicator {
            display: none;
            padding: 10px;
            color: #666;
            font-style: italic;
        }

        .typing-indicator.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏌️ Golf Coach AI</h1>
            <p>Ask me anything about your golf game!</p>
        </div>

        <div class="quick-questions">
            <button onclick="askQuestion('What\\'s my average carry with the Driver?')">📊 Driver Stats</button>
            <button onclick="askQuestion('Compare to PGA Tour averages')">🏆 PGA Comparison</button>
            <button onclick="askQuestion('What should I improve?')">💪 What to Improve</button>
            <button onclick="askQuestion('Summarize my last session')">📈 Session Summary</button>
            <button onclick="askQuestion('Show me patterns in my ball flight')">🎯 Pattern Analysis</button>
            <button onclick="askQuestion('Compare my Driver and 7 Iron')">⚖️ Compare Clubs</button>
        </div>

        <div class="chat-container" id="chatContainer">
            <div class="message coach">
                <div class="avatar">🤖</div>
                <div class="message-content">
                    Hi! I'm your AI Golf Coach with access to all your shot data. Ask me anything about your swing, stats, or how to improve your game!
                </div>
            </div>
        </div>

        <div class="typing-indicator" id="typingIndicator">Coach is thinking...</div>

        <div class="input-container">
            <input
                type="text"
                id="messageInput"
                placeholder="Ask me anything about your golf game..."
                onkeypress="if(event.key==='Enter') sendMessage()"
            />
            <button id="sendButton" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        function addMessage(text, isUser) {
            const container = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'coach'}`;

            messageDiv.innerHTML = `
                <div class="avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">${text}</div>
            `;

            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }

        function showTyping(show) {
            document.getElementById('typingIndicator').classList.toggle('active', show);
            document.getElementById('sendButton').disabled = show;
        }

        async function askQuestion(question) {
            document.getElementById('messageInput').value = question;
            sendMessage();
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();

            if (!message) return;

            // Add user message
            addMessage(message, true);
            input.value = '';

            // Show typing indicator
            showTyping(true);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                // Add coach response
                addMessage(data.response, false);
            } catch (error) {
                addMessage('Sorry, I encountered an error. Please try again.', false);
                console.error('Error:', error);
            } finally {
                showTyping(false);
            }
        }
    </script>
</body>
</html>
    """

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    data = request.json
    message = data.get('message', '')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        response = coach.chat(message)
        return jsonify({
            'response': response,
            'shots_analyzed': coach.total_shots_analyzed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    """Reset conversation"""
    global coach
    coach = create_golf_coach()
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    print("=" * 60)
    print("🏌️  Golf Coach AI - Web Interface")
    print("=" * 60)
    print(f"\n✅ Coach initialized!")
    print(f"📊 Connected to: {coach.full_table_id}")
    print(f"\n🌐 Open your browser and go to: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop the server\n")
    print("=" * 60)

    app.run(debug=True, port=5000)
