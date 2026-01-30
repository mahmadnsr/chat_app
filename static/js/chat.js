let currentChatUser = null;
let inboxTimer = null;
let emojiOpen = false;
let CURRENT_USER = "";

// Global variables for elements
let leftPanel, rightPanel, chatUser, chatBox, userList, input, menuBox, emojiPanel;

/* ================= INITIALIZATION ================= */
document.addEventListener("DOMContentLoaded", () => {
    // Assign elements
    leftPanel = document.getElementById("leftPanel");
    rightPanel = document.getElementById("rightPanel");
    chatUser = document.getElementById("chatUser");
    chatBox = document.getElementById("chatBox");
    userList = document.getElementById("userList");
    input = document.getElementById("messageInput");
    menuBox = document.getElementById("menuBox");
    emojiPanel = document.getElementById("emojiPanel");

    // Fix: Read CURRENT_USER from the data-me attribute we put in the span
    if (chatUser) {
        CURRENT_USER = chatUser.getAttribute("data-me");
    }

    loadConversations();
    
    // Close menu if clicking outside
    document.addEventListener("click", (e) => {
        if (menuBox && menuBox.style.display === "block" && !e.target.closest('.menu')) {
            menuBox.style.display = "none";
        }
    });
});


/* ================= SEARCH USER (Clean & Uniform) ================= */
async function searchUser() {
    const searchInput = document.getElementById("searchUser");
    const uid = searchInput.value.trim();
    
    if (!uid) {
        loadConversations(); 
        return;
    }

    const r = await fetch("/search_user/" + uid);
    const data = await r.json();

    if (data.exists) {
        // Purani list ko load conversations se mangwao pehle taaki stack bana rahe
        await loadConversations(); 

        const existingItems = Array.from(userList.querySelectorAll('strong'));
        const isAlreadyInList = existingItems.some(item => item.textContent === uid);

        if (!isAlreadyInList) {
            const d = document.createElement("div");
            d.className = "user-item"; // Same class for everyone
            d.innerHTML = `
                <div class="user-info">
                    <strong>${uid}</strong>
                    <small>Start a new chat</small>
                </div>
            `;
            d.onclick = () => {
                openChat(uid);
                searchInput.value = ""; 
            };
            userList.prepend(d); 
        }
    }
}

/* ================= LOAD CONVERSATIONS (Clean) ================= */
async function loadConversations() {
    const r = await fetch("/conversations");
    const data = await r.json();
    userList.innerHTML = "";
    
    data.forEach(item => {
        const u = item.user; 
        const d = document.createElement("div");
        d.className = "user-item"; 
        
        const status = (item.last && item.last.msg) ? item.last.msg : "<em>Chat cleared</em>";

        d.innerHTML = `
            <div class="user-info">
                <strong>${u}</strong>
                <small>${status}</small>
            </div>
            ${item.unread > 0 ? `<span class="badge">${item.unread}</span>` : ""}
        `;
        d.onclick = () => openChat(u);
        userList.appendChild(d);
    });
}
/* ================= OPEN CHAT ================= */
function openChat(user) {
    if (inboxTimer) clearInterval(inboxTimer);
    
    currentChatUser = user;
    chatUser.textContent = user;

    leftPanel.classList.add("hidden");
    rightPanel.classList.add("active");

    loadMessages();
    inboxTimer = setInterval(loadMessages, 2000);
}

/* ================= BACK ================= */
async function goBack() {
    // 1. Polling timer band karein
    if (inboxTimer) clearInterval(inboxTimer);
    
    // 2. UI switch karein
    rightPanel.classList.remove("active");
    leftPanel.classList.remove("hidden");
    
    // 3. Sabse important: List refresh karein
    await loadConversations();
}

/* ================= SEND ================= */
async function sendMessage() {
    const m = input.value.trim();
    if (!m || !currentChatUser) return;

    await fetch("/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: currentChatUser, msg: m })
    });

    input.value = "";
    loadMessages();
}

/* ================= LOAD MESSAGES ================= */
async function loadMessages() {
    if (!currentChatUser) return;
    const r = await fetch("/inbox/" + currentChatUser);
    const data = await r.json();

    chatBox.innerHTML = "";
    data.forEach(m => {
        const d = document.createElement("div");
        d.className = m.from === CURRENT_USER ? "bubble sent" : "bubble received";
        d.textContent = m.msg;
        chatBox.appendChild(d);
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}

/* ================= MENU ================= */
function toggleMenu() {
    const menu = document.getElementById("menuBox");
    // Toggle logic
    if (menu.style.display === "block") {
        menu.style.display = "none";
    } else {
        menu.style.display = "block";
    }
}

// Bahar click karne par menu band ho jaye
window.onclick = function(event) {
    if (!event.target.matches('.menu-btn')) {
        const menu = document.getElementById("menuBox");
        if (menu && menu.style.display === "block") {
            menu.style.display = "none";
        }
    }
}
/* ================= DELETE ================= */
async function deleteConversation() {
    if (!currentChatUser) return;
    if (!confirm(`Delete all messages with ${currentChatUser}?`)) return;

    await fetch(`/delete_conversation/${currentChatUser}`, { method: "POST" });
    toggleMenu();
    goBack();
}

/* ================= EMOJI ================= */
function toggleEmoji() {
    const panel = document.getElementById("emojiPanel");
    panel.classList.toggle("hidden");
}

function addEmoji(emoji) {
    const input = document.getElementById("messageInput");
    input.value += emoji;
    input.focus();
    // Optional: Emoji select karne ke baad panel band karna ho to niche wali line rakhein
    // document.getElementById("emojiPanel").classList.add("hidden");
}

/* ================= LOGOUT ================= */
async function logout() {
    await fetch("/logout");
    location.href = "/";
}