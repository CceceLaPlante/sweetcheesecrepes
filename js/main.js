// js/main.js

let currentTypewriterInterval = null

// Select the dialog box element and the paragraph inside it
const dialogBox = document.querySelector('.dialog-wrapper'); // Use querySelector for class
const dialogTextElement = dialogBox ? dialogBox.querySelector('p') : null; // Find the p inside dialogBox

// Select all the art-card elements
const artCards = document.querySelectorAll('.art-card');


const coffeeModalOverlay = document.getElementById('coffee-modal-overlay');
const coffeeModalContent = document.getElementById('coffee-modal-content');
const coffeeSprite = document.getElementById('coffee-sprite');
const coffeeDialogText = document.getElementById('coffee-dialog-text');
const coffeeChoicesContainer = document.getElementById('coffee-choices');
const closeCoffeeModalBtn = document.getElementById('close-coffee-modal-btn');
const orderCoffeeBtn = document.querySelector('.order');

const coffeeEntryArea = document.getElementById('coffee-entry-area');
const coffeeTextInput = document.getElementById('coffee-text-input');
const coffeeSubmitEntryBtn = document.getElementById('coffee-submit-entry-btn');

let conversationData = null ;
let currentNodeId = null;
let currentItem = null;
let entryAnswer = null;
let inventory = []; 
let sparing_numbers = 0;
let killed = false;

function displayNode (nodeId) {

    if (killed) { 
        nodeId = "killed";
    }

    if (!conversationData || !conversationData[nodeId]) {
        console.error(`Node "${nodeId}" not found in conversation data.`);
        if (coffeeDialogText) {
            typewriterEffect(coffeeDialogText, "Hmm, I seem to have lost my train of thought...");
        }
        return;
    }

    currentNodeId = nodeId;
    const node = conversationData[nodeId];
    
    if (killed) {
        coffeeSprite.src = "";
    }
    else if (node.sprite_image && coffeeSprite) {
        /*coffeeSprite.src = node.sprite_image;*/
        coffeeSprite.src = "images/madam.png";
        coffeeSprite.alt = "madame"; 
    } else if (coffeeSprite) {
        coffeeSprite.src = "images/madam.png";
    }

    if (coffeeDialogText && node.sprite_text) {
        let processedText = node.sprite_text;
        if (currentItem && processedText.includes("%ITEM%")) {
            processedText = processedText.replace("%ITEM%", currentItem);
        }

        typewriterEffect(coffeeDialogText, processedText);
    }

    if (coffeeChoicesContainer) {
        coffeeChoicesContainer.innerHTML = ''; 

        if (node.entry_mode) {

            if (coffeeChoicesContainer) coffeeChoicesContainer.style.display = 'none'; 
            if (coffeeEntryArea) coffeeEntryArea.style.display = 'flex'; 

            if (coffeeTextInput) {
                coffeeTextInput.value = ''; // Clear previous input
                coffeeTextInput.placeholder = node.entry_mode.prompt_text || "Type here...";
                coffeeTextInput.focus(); // Focus on the input field
            }
        } else if (node.choices) {

            if (coffeeEntryArea) coffeeEntryArea.style.display = 'none'; 
                if (coffeeChoicesContainer) {
                    coffeeChoicesContainer.style.display = 'block';
                    coffeeChoicesContainer.innerHTML = ''; // Clear old buttons

                    node.choices.forEach(choice => {
                        const button = document.createElement('button');
                        button.classList.add('choice-button');
                        button.textContent = choice.text;
                        button.addEventListener('click', () => handleChoice(choice));
                        coffeeChoicesContainer.appendChild(button);
                    });
                }
            } else {
                if (coffeeChoicesContainer) coffeeChoicesContainer.style.display = 'none';
                if (coffeeEntryArea) coffeeEntryArea.style.display = 'none';
                console.log("Node has no interactive elements:", nodeId);
            }
        
    }
}

function handleEntrySubmit() {
    if (!conversationData || !currentNodeId || !conversationData[currentNodeId] || !conversationData[currentNodeId].entry_mode) {
        console.error("Cannot handle entry: current node is not an entry node or data missing.");
        return;
    }

    const node = conversationData[currentNodeId];
    const entryConfig = node.entry_mode;
    const userInput = coffeeTextInput.value.trim().toLowerCase(); // Get input, trim whitespace, make lowercase for easier comparison

    if (!userInput) return; 

    let navigated = false;
    if (entryConfig.secrets && entryConfig.secrets.length > 0) {
        for (const secret of entryConfig.secrets) {
            if (userInput === secret.input.toLowerCase()) { 

                displayNode(secret.next_node_id);
                navigated = true;
                break; 
            }
        }
    }

    if (!navigated) {
        if (entryConfig.default_next_node_id) {
            displayNode(entryConfig.default_next_node_id);
        } else {
            // Optional: Re-display current prompt or show a generic "try again" message
            typewriterEffect(coffeeDialogText, node.sprite_text + "\n(Hmm, that's not it. Try again?)");
            if (coffeeTextInput) coffeeTextInput.value = ''; // Clear input
        }
    }
}

// Add Event Listener for the submit button (and maybe Enter key on input)
if (coffeeSubmitEntryBtn) {
    coffeeSubmitEntryBtn.addEventListener('click', handleEntrySubmit);
}
if (coffeeTextInput) {
    coffeeTextInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent form submission if it's in a form
            handleEntrySubmit();
        }
    });
}

function handleChoice (choice)  {

    if (choice.item) {
        currentItem = choice.item;
    }

    if (choice.action) {
        if (choice.action == "end_conversation") {
            hideCoffeeModal();
            currentNodeId=null;
        }
        if (choice.action == "save_espresso") {
            inventory.push("espresso");
        }
        if (choice.action == "save_cappuccino") {
            inventory.push("cappuccino");
        }
        if (choice.action == "save_latte") {
            inventory.push("latte");
        }
        if (choice.action == "increase_spare") {
            sparing_numbers ++;
            if (increase_sparing_numbers > 10) {
                displayNode("give")
            }
        }
        if (choice.action == "kill") {
            killed = true; 
            hideCoffeeModal();
        }
        if (choice.action == "check_espresso") {
            if (inventory.includes("espresso")) {
                displayNode("give")
            }
            else {
                displayNode("kill")
            }
        }
        if (choice.action == "check_cappuccino") {
            if (inventory.includes("cappuccino")) {
                displayNode("give")
            }
            else {
                displayNode("kill")
            }
        }
        if (choice.action == "check_latte") {
            if (inventory.includes("latte")) {
                displayNode("give")
            }
            else {
                displayNode("kill")
            }
        }
        
    }

    else if (choice.next_node_id) {
        displayNode(choice.next_node_id);
    }
    else {
        console.warn("no more choice bb",choice);
    }
}

function startConversation() {
    if (conversationData) {
        displayNode("start"); // Assuming "start" is your initial node ID
    } else {
        console.error("Cannot start conversation: Data not loaded.");
    }
}

async function loadConversation () {
    try {
        const response = await fetch("conversation.json");
        
        conversationData = await response.json();
        
    } catch (error)  {
         console.error("Could not load conversation data:", error);

        if (coffeeDialogText) {
            coffeeDialogText.textContent = "Oops! I can't seem to remember my lines right now. Please try again later.";
    }
}
}

loadConversation();


function typewriterEffect(element, text, delay = 30) {
    let index=0;
    element.textContent=""
    clearInterval(currentTypewriterInterval)
    currentTypewriterInterval=null

    currentTypewriterInterval = setInterval( ()=>{
        if (index >= text.length) {
            clearInterval(currentTypewriterInterval);
            currentTypewriterInterval=null;
        }
        else {
            element.textContent += text[index];
            index++;
        }
    } ,delay)
}



function showCoffeeModal() {
    if (coffeeModalOverlay) {
        coffeeModalOverlay.style.display = 'flex';
        startConversation();
    }
}
// Function to hide the modal
function hideCoffeeModal() {
    if (coffeeModalOverlay) {
        coffeeModalOverlay.style.display = 'none';
    }
}


if (orderCoffeeBtn) {
    orderCoffeeBtn.addEventListener('click', () => {
        console.log("Order coffee button clicked!"); 
        showCoffeeModal();

    });
} else {
    console.error("Order coffee button not found!");
}

if (closeCoffeeModalBtn) {
    closeCoffeeModalBtn.addEventListener('click', () => {
        hideCoffeeModal();
    });
}

if (coffeeModalOverlay) {
    coffeeModalOverlay.addEventListener('click', (event) => {
        // Check if the clicked target is the overlay itself
        if (event.target === coffeeModalOverlay) {
            hideCoffeeModal();
        }
    });
}

artCards.forEach(card => {
    card.addEventListener('click', (event) => {
        // Get the specific art-card that was clicked
        const clickedCard = event.currentTarget;

        // Retrieve the text from the data-dialog-text attribute
        const message = clickedCard.dataset.dialogText || "Default message if attribute is missing."; // Add a fallback

        // Update the text content of the dialogTextElement
        if (dialogTextElement) {
           typewriterEffect(dialogTextElement,message)
        } else {
            console.error("Dialog text element not found!"); // Debug
        }

        if (dialogBox) {
            dialogBox.style.display = 'block'; // Or 'flex' or 'grid' if needed for its internal layout
            console.log("Dialog box should be visible now."); // Debug
        } else {
            console.error("Dialog box element not found!"); // Debug
        }
    });
});

// --- Code for closing the dialog ---
if (dialogBox) {
    dialogBox.addEventListener('click', () => {
        // This will hide the dialog if you click ON the dialog box itself.
        // We might want to prevent this if the click was on a button INSIDE the dialog later.
        dialogBox.style.display = 'none';
        console.log("Dialog box hidden by clicking on it."); // Debug
    });
}
