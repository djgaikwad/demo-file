const chatBody = document.getElementById('chat-body');
const buttonContainer = document.getElementById('button-container');
const navButtons = document.getElementById('nav-buttons');

let currentRegion = null;
let messageHistory = [];

// Add message to chat window
function addMessage(text, sender = 'bot') {
    messageHistory.push({ text, sender });
    const msgDiv = document.createElement('div');
    msgDiv.classList.add(sender === 'bot' ? 'bot-message' : 'user-message');
    msgDiv.textContent = text;
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Show buttons given array of options and a click handler
function showButtons(options, onClickHandler) {
    buttonContainer.innerHTML = '';
    options.forEach(option => {
        const btn = document.createElement('button');
        btn.textContent = option;
        btn.classList.add('chat-button');
        btn.onclick = () => onClickHandler(option);
        buttonContainer.appendChild(btn);
    });
    buttonContainer.style.display = 'flex';
    navButtons.style.display = 'flex';
}

// Show region buttons on start or reset
function showRegions() {
    currentRegion = null;
    chatBody.innerHTML = '';
    buttonContainer.innerHTML = '';
    navButtons.style.display = 'none';

    addMessage("Hello! Please select a region to proceed.");
    showButtons(regions, onRegionSelected);
}

// When a region is selected
function onRegionSelected(regionName) {
    currentRegion = regionName;
    addMessage(regionName, 'user');
    addMessage(`You selected "${regionName}". Please select an activity.`);
    showButtons(activities, onActivitySelected);
}

function onActivitySelected(activityName) {
    addMessage(activityName, 'user');

    fetch('/run_activity', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ activity: activityName })
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success'){
            addMessage(data.message);

            // Poll for output file after starting batch
            setTimeout(() => fetchOutputWithRetry(5), 2000);
        } else {
            addMessage(`Error: ${data.message}`);
        }
    })
    .catch(err => addMessage(`Error: ${err}`));
}

// Try fetching output file multiple times
function fetchOutputWithRetry(retries) {
    fetch('/get_output')
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success' && data.content.trim() !== ""){
            addMessage(data.content);
            // addMessage("Output file contents:\n" + data.content);
        } else if (retries > 0) {
            // Retry after short delay
            setTimeout(() => fetchOutputWithRetry(retries - 1), 1500);
        } else {
            addMessage("No output file found or file is empty.");
        }
    })
    .catch(err => addMessage("Error fetching output: " + err));
}


// Back button goes to region selection
function navigateBack() {
    if(currentRegion){
        showRegions();
    }
}

// Reset chat fully
function resetChat() {
    messageHistory = [];
    showRegions();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    showRegions();
});