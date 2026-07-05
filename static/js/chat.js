const chatStream = document.querySelector("#chat-stream");
const chatForm = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const productSelect = document.querySelector("#product-select");
const categorySelect = document.querySelector("#category-select");
const newChatButton = document.querySelector("#new-chat-button");
const promptCards = document.querySelectorAll(".prompt-card");
const sourcePearlsList = document.querySelector("#source-pearls-list");
const sourceCount = document.querySelector("#source-count");
const pinboardList = document.querySelector("#pinboard-list");
const clearPinsButton = document.querySelector("#clear-pins");
const scratchpad = document.querySelector("#scratchpad");

let conversationId = null;
let isLoading = false;
let pinnedItems = [];
const OPENING_MESSAGE = "Hello, I'm ISA, Inogen's Support Assistant. Ask me about an Inogen model, manual, alarm, battery, column replacement, or FAA document.";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactText(value, limit = 220) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 3).trim()}...` : text;
}


function documentUrl(citation) {
  const relativePath = citation?.relative_path;
  if (!relativePath) return "";
  const encodedPath = String(relativePath).split("/").map(encodeURIComponent).join("/");
  const page = Number(citation.page_number);
  return `/api/document/${encodedPath}${page ? `#page=${page}` : ""}`;
}
function scrollToBottom() {
  chatStream.scrollTo({ top: chatStream.scrollHeight, behavior: "smooth" });
}

function setLoading(nextState) {
  isLoading = nextState;
  sendButton.disabled = nextState;
  messageInput.disabled = nextState;
  sendButton.title = nextState ? "Thinking" : "Send";
}

function fileIcon() {
  return `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <path d="M14 2v6h6"></path>
      <path d="M16 13H8M16 17H8M10 9H8"></path>
    </svg>
  `;
}

function citationChipMarkup(citations) {
  if (!citations || citations.length === 0) return "";
  const chips = citations.slice(0, 6).map((citation, index) => {
    const title = escapeHtml(citation.filename || `Source ${index + 1}`);
    const page = citation.page_number || "?";
    const href = documentUrl(citation);
    const content = `${fileIcon()}<span>[${index + 1}] ${title} p.${page}</span>`;
    if (!href) {
      return `<span class="source-chip" title="${title}, page ${page}">${content}</span>`;
    }
    return `<a class="source-chip" href="${href}" target="_blank" rel="noopener" title="${title}, page ${page}">${content}</a>`;
  }).join("");
  return `<div class="source-chip-container">${chips}</div>`;
}

function feedbackPearlsMarkup() {
  return `
    <div class="feedback-container">
      <button class="feedback-pearl" data-feedback="positive" type="button" title="Helpful">
        <span class="feedback-pearl-text">Helpful</span>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.3a2 2 0 0 0 2-1.7l1.4-9A2 2 0 0 0 19.7 9zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
      </button>
      <button class="feedback-pearl" data-feedback="negative" type="button" title="Not helpful">
        <span class="feedback-pearl-text">Not helpful</span>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.7a2 2 0 0 0-2 1.7l-1.4 9A2 2 0 0 0 4.3 15zM17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg>
      </button>
    </div>
  `;
}

function renderSourcePearls(citations) {
  if (!citations || citations.length === 0) {
    sourceCount.textContent = "0";
    sourcePearlsList.innerHTML = `<div class="empty-state">No citations returned for the latest answer.</div>`;
    return;
  }

  sourceCount.textContent = String(citations.length);
  sourcePearlsList.innerHTML = citations.map((citation, index) => {
    const title = escapeHtml(citation.filename || `Source ${index + 1}`);
    const page = escapeHtml(citation.page_number || "?");
    const category = escapeHtml(citation.category || "uncategorized");
    const product = escapeHtml(citation.product || "Unknown");
    const snippet = escapeHtml(compactText(citation.snippet || "", 260));
    const href = documentUrl(citation);
    const titleMarkup = href
      ? `<a class="source-pearl-title" href="${href}" target="_blank" rel="noopener">[${index + 1}] ${title}</a>`
      : `<div class="source-pearl-title">[${index + 1}] ${title}</div>`;
    return `
      <article class="source-pearl">
        ${titleMarkup}
        <div class="source-pearl-meta">${category} - ${product} - page ${page}</div>
        <div class="source-pearl-snippet">${snippet}</div>
      </article>
    `;
  }).join("");
}

function attachFeedbackHandlers(scope) {
  scope.querySelectorAll(".feedback-pearl").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.closest(".feedback-container");
      group.querySelectorAll(".feedback-pearl").forEach((peer) => { peer.disabled = true; });
      button.classList.add("selected");
    });
  });
}

function renderPinboard() {
  if (pinnedItems.length === 0) {
    pinboardList.innerHTML = `<div class="empty-state">Pinned answer excerpts will appear here.</div>`;
    return;
  }
  pinboardList.innerHTML = pinnedItems.map((item) => `
    <article class="pinboard-item">
      <button class="pinboard-remove" type="button" data-pin-id="${item.id}" title="Remove">x</button>
      <div class="pinboard-title">Pinned Message</div>
      <div class="pinboard-text">${escapeHtml(item.text)}</div>
    </article>
  `).join("");
  pinboardList.querySelectorAll(".pinboard-remove").forEach((button) => {
    button.addEventListener("click", () => {
      pinnedItems = pinnedItems.filter((item) => item.id !== button.dataset.pinId);
      renderPinboard();
    });
  });
}

function attachPinHandler(article) {
  const pinButton = article.querySelector(".pin-button");
  if (!pinButton) return;
  pinButton.addEventListener("click", () => {
    const id = article.dataset.messageId;
    const text = compactText(article.querySelector(".message-content")?.innerText || "", 240);
    const existing = pinnedItems.findIndex((item) => item.id === id);
    if (existing >= 0) {
      pinnedItems.splice(existing, 1);
      pinButton.classList.remove("pinned");
    } else {
      pinnedItems.unshift({ id, text });
      pinButton.classList.add("pinned");
    }
    renderPinboard();
  });
}

function renderMessage(role, text, citations = [], isError = false) {
  const article = document.createElement("article");
  const messageId = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  article.dataset.messageId = messageId;
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"} ${isError ? "error-message" : ""}`;
  const avatarText = role === "user" ? "YOU" : "ISA";
  const pinButton = role === "assistant" ? `
    <button class="pin-button" type="button" title="Pin message" aria-label="Pin message">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v6"></path><path d="M2.5 15a9.5 9.5 0 0 1 19 0"></path><path d="M12 15v1a2 2 0 0 1-2 2H8a2 2 0 0 0-2 2v1h12v-1a2 2 0 0 0-2-2h-2a2 2 0 0 1-2-2z"></path></svg>
    </button>
  ` : "";

  article.innerHTML = `
    <div class="avatar">${avatarText}</div>
    <div class="message-body">
      <div class="bubble">
        ${pinButton}
        <div class="message-content">${escapeHtml(text)}</div>
        ${role === "assistant" ? citationChipMarkup(citations) + feedbackPearlsMarkup() : ""}
      </div>
    </div>
  `;
  chatStream.appendChild(article);
  attachFeedbackHandlers(article);
  attachPinHandler(article);
  scrollToBottom();
}

function setCategory(value) {
  categorySelect.value = value;
}

function resetComposer() {
  messageInput.value = "";
  messageInput.style.height = "auto";
}

async function sendMessage(message) {
  const text = (message || messageInput.value).trim();
  if (!text || isLoading) return;

  renderMessage("user", text);
  resetComposer();
  setLoading(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        product: productSelect.value,
        category: categorySelect.value,
        conversation_id: conversationId,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = data.missing_env ? ` Missing: ${data.missing_env.join(", ")}.` : "";
      throw new Error(`${data.error || "Request failed."}${detail}`);
    }

    conversationId = data.conversation_id || conversationId;
    renderSourcePearls(data.citations || []);
    renderMessage("assistant", data.answer || "No answer returned.", data.citations || []);
  } catch (error) {
    renderSourcePearls([]);
    renderMessage("assistant", error.message || "ISA could not answer that request.", [], true);
  } finally {
    setLoading(false);
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage();
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 160)}px`;
});

promptCards.forEach((card) => card.addEventListener("click", () => sendMessage(card.dataset.prompt)));

newChatButton.addEventListener("click", () => {
  conversationId = null;
  pinnedItems = [];
  renderPinboard();
  renderSourcePearls([]);
  chatStream.innerHTML = `
    <article class="message assistant-message">
      <div class="avatar">ISA</div>
      <div class="message-body">
        <div class="bubble">
          <button class="pin-button" type="button" title="Pin message" aria-label="Pin message">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v6"></path><path d="M2.5 15a9.5 9.5 0 0 1 19 0"></path><path d="M12 15v1a2 2 0 0 1-2 2H8a2 2 0 0 0-2 2v1h12v-1a2 2 0 0 0-2-2h-2a2 2 0 0 1-2-2z"></path></svg>
          </button>
          <div class="message-content">${OPENING_MESSAGE}</div>
        </div>
      </div>
    </article>
  `;
  chatStream.querySelectorAll(".assistant-message").forEach(attachPinHandler);
  resetComposer();
  messageInput.focus();
});

clearPinsButton.addEventListener("click", () => { pinnedItems = []; renderPinboard(); });

scratchpad.value = localStorage.getItem("isa_scratchpad") || "";
scratchpad.addEventListener("input", () => localStorage.setItem("isa_scratchpad", scratchpad.value));

chatStream.querySelectorAll(".assistant-message").forEach(attachPinHandler);
renderPinboard();



