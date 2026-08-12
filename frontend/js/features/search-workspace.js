import { searchEntries } from "../core/api.js";
import {
  closeDropdown,
  renderMessage,
  renderResults,
  selectWord,
  setStatus,
  updateHighlight,
} from "../core/ui.js";

export function initSearchWorkspace() {
  const searchInput = document.getElementById("search-input");
  const numberInput = document.getElementById("number-input");
  const headerInput = document.getElementById("header-input");
  const resultsList = document.getElementById("results-list-search");
  const searchBox = document.querySelector(".search-box");
  const searchControls = searchBox?.querySelector(".search-controls");
  const clearSearchToggle = document.getElementById("clear-search-toggle");
  const numberInputToggle = document.getElementById("number-input-toggle");
  const clearButton = document.getElementById("clear-btn");
  const copyButton = document.getElementById("copy-btn");
  const saveButton = document.getElementById("save-btn");
  const headerButton = document.getElementById("headerBtn");
  const savedList = document.getElementById("saved-list");
  const headerText = document.getElementById("header-text");
  const saveStatus = document.getElementById("save-status");

  if (!searchInput || !numberInput || !resultsList || !savedList) return;

  let debounceTimer;
  let highlightedIndex = -1;
  let searchRequestId = 0;
  let header = "";

  const isNumberInputEnabled = () => numberInputToggle?.checked ?? true;

  const focusAfterAdding = () => {
    if (isNumberInputEnabled()) {
      numberInput.focus();
    } else {
      searchInput.focus();
    }
  };

  const chooseWord = (word) => {
    selectWord(word, numberInput, savedList);

    if (clearSearchToggle?.checked) {
      window.clearTimeout(debounceTimer);
      searchRequestId += 1;
      highlightedIndex = -1;
      searchInput.value = "";
      closeDropdown(searchInput, resultsList);
      resultsList.replaceChildren();
    }
  };

  const runSearch = async (prefix, requestId) => {
    try {
      const data = await searchEntries(prefix);
      if (requestId !== searchRequestId) return;
      renderResults(data.words || [], resultsList, searchInput, chooseWord);
    } catch {
      if (requestId !== searchRequestId) return;
      renderMessage("No matches found", searchInput, resultsList);
    }
  };

  searchInput.addEventListener("input", () => {
    window.clearTimeout(debounceTimer);
    highlightedIndex = -1;
    const requestId = ++searchRequestId;
    debounceTimer = window.setTimeout(
      () => runSearch(searchInput.value.trim(), requestId),
      200,
    );
  });

  searchInput.addEventListener("keydown", (event) => {
    const items = resultsList.querySelectorAll(".entry-item:not(.is-empty)");

    if (searchInput.value === "" && event.key === "Backspace" && isNumberInputEnabled()) {
      event.preventDefault();
      numberInput.focus();
    } else if (event.key === "ArrowDown" || (event.key === "Tab" && !event.shiftKey)) {
      event.preventDefault();
      highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
      updateHighlight(items, highlightedIndex);
    } else if (event.key === "ArrowUp" || (event.key === "Tab" && event.shiftKey)) {
      event.preventDefault();
      highlightedIndex = Math.max(highlightedIndex - 1, 0);
      updateHighlight(items, highlightedIndex);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (highlightedIndex >= 0 && items[highlightedIndex]) {
        chooseWord(items[highlightedIndex].dataset.word);
      }
      else {
        highlightedIndex = Math.max(highlightedIndex - 1, 0);
        chooseWord(items[highlightedIndex].dataset.word);
      }
      focusAfterAdding();
    } else if (event.key === "Escape") {
      closeDropdown(searchInput, resultsList);
      focusAfterAdding();
    }
  });

  numberInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      searchInput.focus();
    }
  });

  const updateNumberInputVisibility = () => {
    const enabled = isNumberInputEnabled();
    numberInput.hidden = !enabled;
    numberInput.disabled = !enabled;
    searchControls?.classList.toggle("is-number-disabled", !enabled);
    searchBox?.classList.toggle("is-number-disabled", !enabled);

    if (!enabled && document.activeElement === numberInput) {
      searchInput.focus();
    }
  };

  numberInputToggle?.addEventListener("change", updateNumberInputVisibility);
  updateNumberInputVisibility();

  document.addEventListener("click", (event) => {
    if (!searchBox?.contains(event.target)) {
      closeDropdown(searchInput, resultsList);
    }
  });

  document.addEventListener("dictionary:cleared", () => {
    window.clearTimeout(debounceTimer);
    searchRequestId += 1;
    searchInput.value = "";
    closeDropdown(searchInput, resultsList);
    resultsList.replaceChildren();
  });

  headerButton?.addEventListener("click", () => {
    header = headerInput?.value.trim() || "";
    if (!header) return;
    headerText.textContent = header;
    headerInput.value = "";
  });

  clearButton?.addEventListener("click", () => {
    savedList.value = "";
    searchInput.focus();
  });

  copyButton?.addEventListener("click", async () => {
    const text = `${header ? `${header}\n` : ""}${savedList.value}`;
    await navigator.clipboard.writeText(text);
    setStatus(saveStatus, "Copied to clipboard.", "ok");
  });

  saveButton?.addEventListener("click", () => {
    const text = `${header ? `${header}\n` : ""}${savedList.value}`;
    if (!text) {
      setStatus(saveStatus, "Nothing to save!", "err");
      return;
    }

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.download = header || "saved-words.txt";
    anchor.href = url;
    anchor.click();
    URL.revokeObjectURL(url);
  });
}
