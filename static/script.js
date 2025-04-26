// References to elements within chatbot.html
const chatContainerInner = document.getElementById('chat-container-inner'); // Use the renamed ID
const chatbox = document.getElementById('chatbox');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const loadingIndicator = document.getElementById('loading-indicator');
const resetButton = document.getElementById('reset-button');
// const endChatButton = document.getElementById('end-chat-button'); // Removed
// const goodbyeMessageDiv = document.getElementById('goodbye-message'); // Removed
const minimizeChatButton = document.getElementById('minimize-chat-button'); // Added minimize button


function addMessage(sender, text) {
    const sanitizedText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'clear-both', 'mb-2'); // Assuming Tailwind clear-both utility exists or add custom style
    let bubbleClass = '';
    let bubbleContent = '';
    if (sender === 'user') {
        messageDiv.classList.add('user-message', 'flex', 'justify-end');
        bubbleClass = 'bg-blue-500 text-white'; // User bubble style
        bubbleContent = sanitizedText;
    } else { // Bot message
        messageDiv.classList.add('bot-message', 'flex', 'justify-start');
        bubbleClass = 'bg-sky-100 text-slate-700'; // Bot bubble style
        bubbleContent = sanitizedText; // Make sure bot replies are also sanitized if they contain HTML
    }
    messageDiv.innerHTML = `<div class="${bubbleClass} rounded-lg p-3 max-w-xs lg:max-w-md shadow-sm inline-block">${bubbleContent}</div>`;

    chatbox.insertBefore(messageDiv, loadingIndicator); // Insert before the loading indicator
    // Smooth scroll to the bottom
    chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
}

function showLoading(isLoading) {
    loadingIndicator.style.display = isLoading ? 'flex' : 'none';
    if (isLoading) {
        // Scroll down when loading indicator appears
        chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
    }
}

function setInputDisabled(isDisabled) {
    messageInput.disabled = isDisabled;
    sendButton.disabled = isDisabled;
    // endChatButton.disabled = isDisabled; // Removed

    if (isDisabled) {
        sendButton.classList.add('sending'); // Visual cue for sending
    } else {
        sendButton.classList.remove('sending');
    }

    // Style disabled end chat button (Removed)
    // if (isDisabled) {
    //     endChatButton.classList.add('opacity-50', 'cursor-not-allowed');
    // } else {
    //     endChatButton.classList.remove('opacity-50', 'cursor-not-allowed');
    // }
}

messageForm.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent default form submission
    const userMessage = messageInput.value.trim();

    if (userMessage) {
        addMessage('user', userMessage);
        messageInput.value = ''; // Clear the input field
        setInputDisabled(true); // Disable input while processing
        showLoading(true); // Show loading indicator

        try {
            // Send message to the backend
            const response = await fetch('/chat', { // Ensure this path is correct
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage }),
            });

            showLoading(false); // Hide loading indicator

            if (!response.ok) {
                // Try to parse error from response, otherwise use status text
                let errorMsg = `HTTP error! Status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorData.message || errorMsg;
                } catch (e) { /* Ignore if response is not JSON */ }
                throw new Error(errorMsg);
            }

            const data = await response.json();

            // Display bot reply or error
            if (data.bot_reply) {
                addMessage('bot', data.bot_reply);
            } else if (data.error) {
                 addMessage('bot', `Sorry, an error occurred: ${data.error}`);
            } else {
                 addMessage('bot', "Sorry, I received an unexpected response.");
            }

        } catch (error) {
            console.error('Error sending/receiving message:', error);
            showLoading(false); // Hide loading indicator on error
            // Provide more specific error feedback to the user
            addMessage('bot', `Sorry, I couldn't connect or process that. Error: ${error.message}. Please try again.`);
        } finally {
            setInputDisabled(false); // Re-enable input
            messageInput.focus(); // Focus back on the input field
        }
    }
});

// Function to get the initial bot message on load
async function getInitialMessage() {
    showLoading(true);
    setInputDisabled(true);
    try {
        // Post null message to get initial greeting
        const response = await fetch('/chat', { // Ensure this path is correct
             method: 'POST',
             headers: {'Content-Type': 'application/json'},
             body: JSON.stringify({ message: null }) // Sending null or specific init signal
        });
        if (!response.ok) {
             let errorMsg = `Failed to get initial message. Status: ${response.status}`;
             try { const errorData = await response.json(); errorMsg = errorData.error || errorData.message || errorMsg; } catch (e) {}
             throw new Error(errorMsg);
        }
        const data = await response.json();
        if (data.bot_reply) {
             addMessage('bot', data.bot_reply);
        } else {
             // Fallback initial message
             addMessage('bot', "Hello! Ready when you are.");
        }
    } catch(error) {
        console.error("Error getting initial message:", error);
        addMessage('bot', `Hello! I had trouble starting: ${error.message}. Try sending a message.`);
    } finally {
        showLoading(false);
        setInputDisabled(false);
        messageInput.focus();
    }
}

// Reset Conversation Listener
resetButton.addEventListener('click', async () => {
    // Confirmation dialog
    if (confirm("Are you sure you want to reset the conversation?")) {
        // Clear current messages visually first
        const messages = chatbox.querySelectorAll('.message:not(#loading-indicator)');
        messages.forEach(msg => msg.remove());

        showLoading(true); // Show loading
        setInputDisabled(true); // Disable input

        try {
            // Call the backend reset endpoint
            const response = await fetch('/reset', { method: 'POST' }); // Ensure this path is correct
            if (!response.ok) {
                throw new Error('Failed to reset session on server.');
            }
            // Handle success response from server
            const data = await response.json();
            if (data.status === 'success' && data.initial_message) {
                 addMessage('bot', data.initial_message); // Display new initial message from server
            } else {
                 addMessage('bot', "Conversation reset. Hello again!"); // Fallback reset message
            }
        } catch (error) {
            console.error("Error resetting conversation:", error);
            addMessage('bot', "Couldn't reset session properly. Please refresh if needed.");
        } finally {
            showLoading(false); // Hide loading
            setInputDisabled(false); // Enable input
            messageInput.focus(); // Focus input
        }
    }
});

// Minimize/Close Chat Listener (sends message to parent window)
minimizeChatButton.addEventListener('click', () => {
    console.log("Minimize/Close button clicked inside iframe");
    // Send a message to the parent window (index.html) to close the iframe
    if (window.parent && window.parent !== window) {
         window.parent.postMessage('close-chat', '*'); // '*' allows any origin, restrict if needed
    } else {
        console.warn("Cannot send message: Not inside an iframe or parent inaccessible.");
        // Fallback behavior if not in iframe? Maybe hide itself?
        // chatContainerInner.style.display = 'none';
    }
});


// Removed End Chat Button Listener
// endChatButton.addEventListener('click', () => {
//     if (confirm("Are you sure you want to end this conversation?")) {
//         console.log("Ending chat.");
//         chatContainerInner.style.display = 'none'; // Use the correct container ID
//         goodbyeMessageDiv.style.display = 'block';
//         // Optional: Inform the backend the chat has ended
//         // fetch('/end_chat', { method: 'POST' });
//     }
// });


// Get initial message when the chatbot loads
window.addEventListener('load', getInitialMessage);