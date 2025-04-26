const chatToggleButton = document.getElementById('chat-toggle-button');
const floatingChatContainer = document.getElementById('floating-chat-container');
const closeChatButton = document.getElementById('close-chat-button'); // Get the new close button
const chatbotIframe = document.getElementById('chatbot-iframe'); // Get the iframe

// Function to toggle chat visibility using Tailwind's 'hidden' class
function toggleChat() {
    // Check if the container is currently hidden
    const isHidden = floatingChatContainer.classList.contains('hidden');
    if (isHidden) {
        floatingChatContainer.classList.remove('hidden'); // Show it
        chatToggleButton.title = "Close Chat";
        // Consider if you need to add/remove 'open' class for styling the button itself
        // chatToggleButton.classList.add('open');
    } else {
        floatingChatContainer.classList.add('hidden'); // Hide it
        chatToggleButton.title = "Open Chat";
        // Consider if you need to add/remove 'open' class for styling the button itself
        // chatToggleButton.classList.remove('open');
    }
    // Optional: Reload iframe or send message to it when opened/closed
    // chatbotIframe.contentWindow.postMessage('chat-toggled', '*');
}

// Event listener for the main toggle button
chatToggleButton.addEventListener('click', toggleChat);

// Event listener for the close button inside the container
closeChatButton.addEventListener('click', () => {
    // Only toggle if it's currently not hidden (i.e., visible)
    if (!floatingChatContainer.classList.contains('hidden')) {
        toggleChat(); // Use the same toggle function to close
    }
});

// Listen for messages from the iframe (e.g., the minimize button inside chatbot.html)
window.addEventListener('message', (event) => {
    // Add origin check for security if chatbot is on a different domain
    // if (event.origin !== 'YOUR_CHATBOT_ORIGIN') { // Replace with actual origin if needed
    //     console.warn("Message received from unexpected origin:", event.origin);
    //     return;
    // }

    if (event.data === 'close-chat') {
        console.log("Received 'close-chat' message from iframe");
        // Only toggle if it's currently not hidden (i.e., visible)
        if (!floatingChatContainer.classList.contains('hidden')) {
            toggleChat(); // Close the chat window
        }
    }
});

// Optional: Close chat if user clicks outside the chat window
// document.addEventListener('click', (event) => {
//     if (!floatingChatContainer.classList.contains('hidden') && // If visible
//         !floatingChatContainer.contains(event.target) &&      // Click is outside container
//         !chatToggleButton.contains(event.target)) {             // Click is not the toggle button
//         toggleChat(); // Close it
//     }
// });