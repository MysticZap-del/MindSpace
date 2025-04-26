const chatToggleButton = document.getElementById('chat-toggle-button');
const floatingChatContainer = document.getElementById('floating-chat-container');
const closeChatButton = document.getElementById('close-chat-button'); // Get the new close button
const chatbotIframe = document.getElementById('chatbot-iframe'); // Get the iframe

// Function to toggle chat visibility
function toggleChat() {
    const isVisible = floatingChatContainer.classList.contains('visible');
    if (isVisible) {
        floatingChatContainer.classList.remove('visible');
        chatToggleButton.classList.remove('open'); // Optional: change button style
        chatToggleButton.title = "Open Chat";
    } else {
        floatingChatContainer.classList.add('visible');
        chatToggleButton.classList.add('open'); // Optional: change button style
        chatToggleButton.title = "Close Chat";
        // Optional: Reload iframe or send message to it when opened
        // chatbotIframe.contentWindow.postMessage('chat-opened', '*');
    }
}

// Event listener for the main toggle button
chatToggleButton.addEventListener('click', toggleChat);

// Event listener for the close button inside the container
closeChatButton.addEventListener('click', () => {
    if (floatingChatContainer.classList.contains('visible')) {
        toggleChat(); // Use the same toggle function to close
    }
});

// Listen for messages from the iframe (e.g., the minimize button inside chatbot.html)
window.addEventListener('message', (event) => {
    // Add origin check for security if chatbot is on a different domain
    // if (event.origin !== 'expected-chatbot-origin') {
    //     console.warn("Message received from unexpected origin:", event.origin);
    //     return;
    // }

    if (event.data === 'close-chat') {
        console.log("Received 'close-chat' message from iframe");
        if (floatingChatContainer.classList.contains('visible')) {
            toggleChat(); // Close the chat window
        }
    }
});

// Optional: Close chat if user clicks outside the chat window
// document.addEventListener('click', (event) => {
//     if (floatingChatContainer.classList.contains('visible') &&
//         !floatingChatContainer.contains(event.target) &&
//         !chatToggleButton.contains(event.target)) {
//         toggleChat();
//     }
// });