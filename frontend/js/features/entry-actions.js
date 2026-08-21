import {
  deleteAllEntries,
  deleteEntry,
  insertEntry,
  previewEntries,
  searchEntries,
  uploadEntries,
} from "../core/api.js";
import {
  closeDropdown,
  formatError,
  renderMessage,
  renderResults,
  setStatus,
  updateHighlight,
} from "../core/ui.js";

const CSV_PREVIEW_PAGE_SIZE = 75;
const FAILURE_DETAILS_PAGE_SIZE = 50;
const FAILURE_LABELS = {
  all: "All failures",
  duplicate: "Duplicates",
  invalid: "Invalid entries",
  server_error: "Server errors",
};

export function initEntryActions() {
  const addInput = document.getElementById("add-input");
  const fileInput = document.getElementById("file");
  const columnInput = document.getElementById("csv-header-input");
  const addButton = document.getElementById("add-btn");
  const uploadButton = document.getElementById("upload-btn");
  const addStatus = document.getElementById("add-status");
  const uploadStatus = document.getElementById("upload-status");
  const viewImportFailuresButton = document.getElementById("view-import-failures-btn");
  const failureDetailsDialog = document.getElementById("import-failures-dialog");
  const failureDetailCount = document.getElementById("failure-detail-count");
  const failureDetailList = document.getElementById("failure-detail-list");
  const failureDetailPage = document.getElementById("failure-detail-page");
  const previousFailurePageButton = document.getElementById("previous-failure-page-btn");
  const nextFailurePageButton = document.getElementById("next-failure-page-btn");
  const closeFailureDetailsButton = document.getElementById("close-failure-details-btn");
  const failureFilterButtons = failureDetailsDialog?.querySelectorAll("[data-failure-filter]") || [];
  const failureCountElements = failureDetailsDialog?.querySelectorAll("[data-failure-count]") || [];
  const previewDialog = document.getElementById("csv-preview-dialog");
  const previewCount = document.getElementById("csv-preview-count");
  const previewList = document.getElementById("csv-preview-list");
  const previewPage = document.getElementById("csv-preview-page");
  const previousCsvPageButton = document.getElementById("previous-csv-page-btn");
  const nextCsvPageButton = document.getElementById("next-csv-page-btn");
  const previewStatus = document.getElementById("csv-preview-status");
  const confirmUploadButton = document.getElementById("confirm-upload-btn");
  const cancelUploadButton = document.getElementById("cancel-upload-btn");
  const deleteInput = document.getElementById("delete-input");
  const deleteButton = document.getElementById("delete-btn");
  const deleteAllButton = document.getElementById("delete-all-btn");
  const deleteStatus = document.getElementById("delete-status");
  const deleteResults = document.getElementById("results-list-delete");
  const confirmationDialog = document.getElementById("delete-all-dialog");
  const confirmDeleteAllButton = document.getElementById("confirm-delete-all-btn");
  const cancelDeleteAllButton = document.getElementById("cancel-delete-all-btn");
  const dialogStatus = document.getElementById("delete-all-dialog-status");
  const resultsList = document.getElementById("results-list-delete");
  const deleteBox = document.querySelector(".delete-box");

  let debounceTimer;
  let highlightedIndex = -1;
  let pendingUpload = null;
  let uploadInProgress = false;
  let csvPreviewPage = 0;
  let failureDetailsPage = 0;
  let activeFailureFilter = "all";
  let importFailures = {
    all: [],
    duplicate: [],
    invalid: [],
    server_error: [],
  };

  const deleteAllErrorMessage = (error) => {
    return formatError(error.detail, "Could not delete all entries.");
  };

  const groupFailures = (failures) => {
    const groups = {
      all: [...failures],
      duplicate: [],
      invalid: [],
      server_error: [],
    };

    for (const item of failures) {
      switch (Number(item.status_code)) {
        case 400:
        case 422:
          groups.invalid.push(item);
          break;
        case 409:
          groups.duplicate.push(item);
          break;
        default:
          groups.server_error.push(item);
      }
    }

    return groups;
  };

  const renderFailureDetails = (requestedPage = 0) => {
    const failures = importFailures[activeFailureFilter] || [];
    const pageCount = Math.max(
      1,
      Math.ceil(failures.length / FAILURE_DETAILS_PAGE_SIZE),
    );
    failureDetailsPage = Math.min(Math.max(requestedPage, 0), pageCount - 1);
    const start = failureDetailsPage * FAILURE_DETAILS_PAGE_SIZE;
    const end = Math.min(start + FAILURE_DETAILS_PAGE_SIZE, failures.length);

    if (failureDetailList) {
      const items = document.createDocumentFragment();
      for (const failure of failures.slice(start, end)) {
        const item = document.createElement("li");
        const word = document.createElement("strong");
        const reason = document.createElement("span");
        word.textContent = String(failure.word);
        reason.textContent = `${failure.reason} (HTTP ${failure.status_code})`;
        item.append(word, reason);
        items.append(item);
      }
      failureDetailList.replaceChildren(items);
      failureDetailList.scrollTop = 0;
    }

    if (failureDetailCount) {
      failureDetailCount.textContent = `${FAILURE_LABELS[activeFailureFilter]}: ${failures.length}`;
    }
    if (failureDetailPage) {
      failureDetailPage.textContent = failures.length
        ? `Failures ${start + 1}-${end} of ${failures.length} · Page ${failureDetailsPage + 1} of ${pageCount}`
        : "No failures in this category";
    }
    if (previousFailurePageButton) {
      previousFailurePageButton.disabled = failureDetailsPage === 0;
    }
    if (nextFailurePageButton) {
      nextFailurePageButton.disabled = failureDetailsPage >= pageCount - 1;
    }

    for (const button of failureFilterButtons) {
      const selected = button.dataset.failureFilter === activeFailureFilter;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    }
  };

  const setImportFailures = (failures) => {
    importFailures = groupFailures(failures);
    activeFailureFilter = "all";
    failureDetailsPage = 0;
    if (viewImportFailuresButton) {
      viewImportFailuresButton.hidden = failures.length === 0;
    }
    for (const element of failureCountElements) {
      const category = element.dataset.failureCount;
      element.textContent = String(importFailures[category]?.length || 0);
    }
  };

  const performUpload = async () => {
    if (!pendingUpload) return;

    const { entries } = pendingUpload;
    uploadInProgress = true;
    if (confirmUploadButton) confirmUploadButton.disabled = true;
    if (cancelUploadButton) cancelUploadButton.disabled = true;
    setStatus(previewStatus, "Importing entries…");

    try {
      const data = await uploadEntries(entries);
      const insertedCount = data.inserted?.length || 0;
      const failures = Array.isArray(data.failed) ? data.failed : [];
      const groupedFailures = groupFailures(failures);
      const failuresSummary = failures.length
        ? `Duplicate entries: ${groupedFailures.duplicate.length}\nInvalid entries: ${groupedFailures.invalid.length}\nServer errors: ${groupedFailures.server_error.length}`
        : "";
      const summary = `${insertedCount} inserted, ${failures.length} failed.`;

      setImportFailures(failures);
      setStatus(
        uploadStatus,
        failuresSummary ? `${summary}\n${failuresSummary}` : summary,
        failures.length ? "err" : "ok",
      );
      previewDialog?.close();
      pendingUpload = null;
      clearCsvPreview();
    } catch (error) {
      setStatus(
        previewStatus,
        formatError(error.detail, "Could not import the file."),
        "err"
      );
    } finally {
      uploadInProgress = false;
      if (confirmUploadButton) confirmUploadButton.disabled = false;
      if (cancelUploadButton) cancelUploadButton.disabled = false;
    }
  };

  const renderCsvPreview = (entries, requestedPage = 0) => {
    if (previewCount) previewCount.textContent = String(entries.length);
    if (!previewList) return;

    const pageCount = Math.max(1, Math.ceil(entries.length / CSV_PREVIEW_PAGE_SIZE));
    csvPreviewPage = Math.min(Math.max(requestedPage, 0), pageCount - 1);
    const start = csvPreviewPage * CSV_PREVIEW_PAGE_SIZE;
    const end = Math.min(start + CSV_PREVIEW_PAGE_SIZE, entries.length);
    const items = document.createDocumentFragment();
    for (const entry of entries.slice(start, end)) {
      const item = document.createElement("li");
      item.textContent = String(entry);
      items.append(item);
    }
    previewList.replaceChildren(items);
    previewList.scrollTop = 0;

    if (previewPage) {
      previewPage.textContent = entries.length
        ? `Entries ${start + 1}-${end} of ${entries.length} · Page ${csvPreviewPage + 1} of ${pageCount}`
        : "No entries";
    }
    if (previousCsvPageButton) previousCsvPageButton.disabled = csvPreviewPage === 0;
    if (nextCsvPageButton) nextCsvPageButton.disabled = csvPreviewPage >= pageCount - 1;
  };

  const clearCsvPreview = () => {
    previewList?.replaceChildren();
    if (previewPage) previewPage.textContent = "";
    csvPreviewPage = 0;
  };

  uploadButton?.addEventListener("click", async () => {
    if (!fileInput?.files?.length) {
      setStatus(uploadStatus, "Select a file first.", "err");
      return;
    }

    const file = fileInput.files[0];
    const column = columnInput?.value.trim() || "";
    uploadButton.disabled = true;
    setImportFailures([]);
    setStatus(uploadStatus, "Parsing preview…");

    try {
      const data = await previewEntries(file, column);
      const entries = Array.isArray(data.entries) ? data.entries : [];

      pendingUpload = { entries };
      renderCsvPreview(entries);
      setStatus(previewStatus, "");
      setStatus(uploadStatus, "");
      if (confirmUploadButton) confirmUploadButton.disabled = (entries.length === 0);

      if (typeof previewDialog?.showModal === "function") {
        previewDialog.showModal();
      } else if (window.confirm(`Insert ${entries.length} entries?`)) {
        await performUpload();
      } else {
        pendingUpload = null;
        clearCsvPreview();
      }
    } catch (error) {
      pendingUpload = null;
      setStatus(
        uploadStatus,
        formatError(error.detail, "Could not parse the file."),
        "err"
      );
    } finally {
      uploadButton.disabled = false;
    }
  });

  confirmUploadButton?.addEventListener("click", performUpload);
  previousCsvPageButton?.addEventListener("click", () => {
    if (!pendingUpload) return;
    renderCsvPreview(pendingUpload.entries, csvPreviewPage - 1);
  });
  nextCsvPageButton?.addEventListener("click", () => {
    if (!pendingUpload) return;
    renderCsvPreview(pendingUpload.entries, csvPreviewPage + 1);
  });
  cancelUploadButton?.addEventListener("click", () => {
    pendingUpload = null;
    clearCsvPreview();
    previewDialog?.close();
  });
  previewDialog?.addEventListener("cancel", (event) => {
    if (uploadInProgress) {
      event.preventDefault();
      return;
    }
    pendingUpload = null;
    clearCsvPreview();
  });

  viewImportFailuresButton?.addEventListener("click", () => {
    activeFailureFilter = "all";
    renderFailureDetails(0);
    if (typeof failureDetailsDialog?.showModal === "function") {
      failureDetailsDialog.showModal();
    }
  });

  for (const button of failureFilterButtons) {
    button.addEventListener("click", () => {
      activeFailureFilter = button.dataset.failureFilter || "all";
      renderFailureDetails(0);
    });
  }

  previousFailurePageButton?.addEventListener("click", () => {
    renderFailureDetails(failureDetailsPage - 1);
  });

  nextFailurePageButton?.addEventListener("click", () => {
    renderFailureDetails(failureDetailsPage + 1);
  });

  closeFailureDetailsButton?.addEventListener("click", () => {
    failureDetailsDialog?.close();
  });

  addButton?.addEventListener("click", async () => {
    const word = addInput?.value.trim();
    if (!word) {
      setStatus(addStatus, "Type a word first.", "err");
      return;
    }

    addButton.disabled = true;

    try {
      const data = await insertEntry(word);
      setStatus(addStatus, data.message || `Added "${word}".`, "ok");
      addInput.value = "";
    } catch (error) {
      setStatus(
        addStatus,
        formatError(error.detail, `Could not add "${word}".`),
        "err"
      );
    } finally {
      addButton.disabled = false;
    }
  });

  const searchForDeletion = async (prefix) => {
    try {
      const data = await searchEntries(prefix);
      renderResults(data.words || [], deleteResults, deleteInput, (word) => {
        deleteInput.value = word;
      });
    } catch {
      renderMessage("No matches found", deleteInput, deleteResults);
    }
  };

  deleteInput?.addEventListener("input", () => {
    window.clearTimeout(debounceTimer);
    highlightedIndex = -1;
    debounceTimer = window.setTimeout(
      () => searchForDeletion(deleteInput.value.trim()),
      200
    );
  });

  deleteInput?.addEventListener("keydown", (event) => {
    const items = deleteResults.querySelectorAll(".entry-item:not(.is-empty)");

    if (!deleteResults.classList.contains("is-open") || items.length === 0) {
      if (!deleteInput.value) return;
    }

    if (event.key === "ArrowDown" || (event.key === "Tab" && !event.shiftKey)) {
      event.preventDefault();
      highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
      updateHighlight(items, highlightedIndex);
    } else if (event.key === "ArrowUp" || (event.key === "Tab" && event.shiftKey)) {
      event.preventDefault();
      highlightedIndex = Math.max(highlightedIndex - 1, 0);
      updateHighlight(items, highlightedIndex);
    } else if (event.key === "Enter" && highlightedIndex >= 0 && items[highlightedIndex]) {
      event.preventDefault();
      deleteInput.value = items[highlightedIndex].dataset.word;
      closeDropdown(deleteInput, deleteResults);
    } else if (event.key === "Escape") {
      closeDropdown(deleteInput, deleteResults);
    }
  });

  deleteButton?.addEventListener("click", async () => {
    const word = deleteInput?.value.trim();
    if (!word) {
      setStatus(deleteStatus, "Type a word first.", "err");
      return;
    }

    deleteButton.disabled = true;

    try {
      const data = await deleteEntry(word);
      setStatus(deleteStatus, data.message || `Deleted "${word}".`, "ok");
      deleteInput.value = "";
      closeDropdown(deleteInput, deleteResults);
    } catch (error) {
      setStatus(
        deleteStatus,
        formatError(error.detail, `Could not delete "${word}".`),
        "err"
      );
    } finally {
      deleteButton.disabled = false;
    }
  });

  const performDeleteAll = async () => {
    deleteAllButton.disabled = true;
    if (confirmDeleteAllButton) confirmDeleteAllButton.disabled = true;
    if (cancelDeleteAllButton) cancelDeleteAllButton.disabled = true;
    confirmationDialog?.close();
    setStatus(deleteStatus, "Deleting every entry…");

    try {
      const data = await deleteAllEntries();
      setStatus(deleteStatus, data.message || "Deleted all entries.", "ok");
      deleteInput.value = "";
      closeDropdown(deleteInput, deleteResults);
      deleteResults.replaceChildren();
      document.dispatchEvent(new CustomEvent("dictionary:cleared"));
    } catch (error) {
      setStatus(
        deleteStatus,
        deleteAllErrorMessage(error),
        "err"
      );
    } finally {
      deleteAllButton.disabled = false;
      if (confirmDeleteAllButton) confirmDeleteAllButton.disabled = false;
      if (cancelDeleteAllButton) cancelDeleteAllButton.disabled = false;
    }
  };

  deleteAllButton?.addEventListener("click", () => {
    setStatus(dialogStatus, "");

    if (typeof confirmationDialog?.showModal === "function") {
      confirmationDialog.showModal();
      return;
    }

    if (window.confirm("Delete every dictionary entry? This cannot be undone.")) {
      performDeleteAll();
    }
  });

  confirmDeleteAllButton?.addEventListener("click", performDeleteAll);
  cancelDeleteAllButton?.addEventListener("click", () => confirmationDialog?.close());

  document.addEventListener("click", (event) => {
    if (!deleteBox?.contains(event.target)) {
      closeDropdown(deleteInput, resultsList);
    }
  });
}
