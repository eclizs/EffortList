import { searchEntries } from "../core/api.js";
import {
  closeDropdown,
  renderMessage,
  renderResults,
  selectWord,
  setStatus,
  updateHighlight,
} from "../core/ui.js";

const SAVED_PREVIEW_PAGE_SIZE = 200;

async function copyText(text) {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
    
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.readOnly = true;
  textarea.setAttribute("aria-hidden", "true");
  textarea.style.position = "fixed";
  textarea.style.inset = "0 auto auto -9999px";
  textarea.style.opacity = "0";
  textarea.style.fontSize = "16px";
  document.body.append(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);

  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

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
  const previewSaveButton = document.getElementById("preview-save-btn");
  const downloadButton = document.getElementById("download-btn");
  const headerButton = document.getElementById("headerBtn");
  const savedList = document.getElementById("saved-list");
  const headerText = document.getElementById("header-text");
  const saveStatus = document.getElementById("save-status");
  const savedBufferDialog = document.getElementById("saved-buffer-dialog");
  const savedBufferPreview = document.getElementById("saved-buffer-preview");
  const savedBufferPage = document.getElementById("saved-buffer-page");
  const previousBufferPageButton = document.getElementById("previous-buffer-page-btn");
  const nextBufferPageButton = document.getElementById("next-buffer-page-btn");
  const closeBufferPreviewButton = document.getElementById("close-buffer-preview-btn");

  if (!searchInput || !numberInput || !resultsList || !savedList) return;

  let debounceTimer;
  let highlightedIndex = -1;
  let searchRequestId = 0;
  let header = "";
  let savedBuffer = null;
  let savedPreviewLines = [];
  let savedPreviewPage = 0;

  const renderSavedPreviewPage = () => {
    const pageCount = Math.max(
      1,
      Math.ceil(savedPreviewLines.length / SAVED_PREVIEW_PAGE_SIZE),
    );
    savedPreviewPage = Math.min(Math.max(savedPreviewPage, 0), pageCount - 1);

    const start = savedPreviewPage * SAVED_PREVIEW_PAGE_SIZE;
    const end = Math.min(start + SAVED_PREVIEW_PAGE_SIZE, savedPreviewLines.length);
    if (savedBufferPreview) {
      savedBufferPreview.value = savedPreviewLines.slice(start, end).join("\n");
      savedBufferPreview.scrollTop = 0;
      savedBufferPreview.scrollLeft = 0;
    }
    if (savedBufferPage) {
      savedBufferPage.textContent = savedPreviewLines.length
        ? `Lines ${start + 1}–${end} of ${savedPreviewLines.length} · Page ${savedPreviewPage + 1} of ${pageCount}`
        : "No saved lines";
    }
    if (previousBufferPageButton) {
      previousBufferPageButton.disabled = savedPreviewPage === 0;
    }
    if (nextBufferPageButton) {
      nextBufferPageButton.disabled = savedPreviewPage >= pageCount - 1;
    }
  };

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
      if(isNumberInputEnabled()) numberInput.value = "";
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
      else if (items.length > 0) {
        highlightedIndex = Math.max(highlightedIndex - 1, 0);
        chooseWord(items[highlightedIndex].dataset.word);
      }
      else
      {
        chooseWord(searchInput.value);
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
    if (!text) {
      setStatus(saveStatus, "Nothing to copy!", "err");
      return;
    }

    const copied = await copyText(text);
    setStatus(
      saveStatus,
      copied ? "Copied to clipboard." : "Could not copy to clipboard.",
      copied ? "ok" : "err",
    );
  });

  saveButton?.addEventListener("click", () => {
    const text = `${header ? `${header}\n` : ""}${savedList.value}`;
    if (!text) {
      setStatus(saveStatus, "Nothing to save!", "err");
      return;
    }

    if (savedBuffer) {
      savedBuffer.text = `${savedBuffer.text.replace(/\n+$/, "")}\n${text}`;
    } else {
      savedBuffer = {
        filename: header || "saved-words.txt",
        text,
      };
    }
    setStatus(saveStatus, "Successfully saved the list.", "ok");
  });

  previewSaveButton?.addEventListener("click", () => {
    if (!savedBuffer) {
      setStatus(saveStatus, "Nothing to preview!", "err");
      return;
    }

    savedPreviewLines = savedBuffer.text.split("\n");
    savedPreviewPage = 0;
    renderSavedPreviewPage();
    if (typeof savedBufferDialog?.showModal === "function") {
      savedBufferDialog.showModal();
    }
  });

  previousBufferPageButton?.addEventListener("click", () => {
    savedPreviewPage -= 1;
    renderSavedPreviewPage();
  });

  nextBufferPageButton?.addEventListener("click", () => {
    savedPreviewPage += 1;
    renderSavedPreviewPage();
  });

  closeBufferPreviewButton?.addEventListener("click", () => {
    savedBufferDialog?.close();
  });

  savedBufferDialog?.addEventListener("close", () => {
    savedPreviewLines = [];
    if (savedBufferPreview) savedBufferPreview.value = "";
  });

  downloadButton?.addEventListener("click", () => {
    if (!savedBuffer) {
      setStatus(saveStatus, "Nothing to download!", "err");
      return;
    }

    const blob = new Blob([savedBuffer.text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.download = savedBuffer.filename;
    anchor.href = url;
    anchor.click();
    URL.revokeObjectURL(url);
    savedBuffer = null;
    savedPreviewLines = [];
    if (savedBufferPreview) savedBufferPreview.value = "";
    setStatus(saveStatus, "Downloaded successfully.", "ok");
  });
}
