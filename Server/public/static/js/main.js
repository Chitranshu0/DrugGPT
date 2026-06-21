import { marked } from './utils/marked.esm.js';
import DOMPurify from './utils/purify.es.mjs';

const CHAT_ENDPOINT = "/chat-completion";

let conversation = [];

document.addEventListener("DOMContentLoaded", (event) => {
    const CHAT_CONTAINER = document.getElementById("chat-content");
    const QUERY_BOX = document.getElementById("query-input");
    const QUERY_BTN = document.getElementById("query-btn");

    QUERY_BOX.addEventListener("keyup", (key) => {
        if(key.key === "Enter") { QUERY_BTN.click(); }
    });

    QUERY_BTN.addEventListener("click", async () => {
        const query = QUERY_BOX.value;
        QUERY_BOX.value = "";
        if (!query.trim()) { 
            const composer = document.querySelector(".composer");
            composer.classList.remove("shake");
            void composer.offsetWidth;
            composer.classList.add("shake");
            return;
        }

        document.body.classList.add("chat-started");
        const chat = { role: "user", message: query };
        appendChat(chat, CHAT_CONTAINER);

        const loader = document.createElement("div");
        loader.className = "typing-indicator";
        loader.innerHTML = `<span></span><span></span><span></span>`
        CHAT_CONTAINER.append(loader);

        try{
            const response = await fetchJSON(chat, CHAT_ENDPOINT);
            // const response = await fetchJSON(conversation, CHAT_ENDPOINT);
            const answer = { role: response.role, message: response.message };
            loader.remove(); appendChat(answer, CHAT_CONTAINER);
        }
        catch (error) {
            const answer = { role: "error", message: error.message };
            loader.remove(); appendChat(answer, CHAT_CONTAINER);
        }

    });

});

function appendChat(chat, container) {
    const chatElement = document.createElement("div");
    chatElement.classList.add("chat-message");
    if(chat.role === "user") { 
        chatElement.className = "user-chat";
        chatElement.textContent = chat.message;
    }
    else if (chat.role === "bot") {
        chatElement.className = "bot-chat";
        const mdFormatted = marked.parse(chat.message);
        const mdFiltered = DOMPurify.sanitize(mdFormatted);
        chatElement.innerHTML = mdFiltered;
        // chatElement.innerHTML = chat.message;
    }
    else {
        chatElement.className = "error-chat";
        chatElement.textContent = chat.message;
        container.append(chatElement);
        return;
    }
    conversation.push(chat);
    container.append(chatElement);
    scrollChat(chatElement);
}

function scrollChat(container) {
    container.scrollTo({
        top: container.scrollHeight,
        behaviour: "smooth"
    });
}

async function fetchJSON(payload, url) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if(!response.ok) {
        throw new Error(`Error ${response.status}!`);
    }
    const data = await response.json();
    console.log(data);
    return data;
}

