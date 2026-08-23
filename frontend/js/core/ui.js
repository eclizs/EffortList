export function formatError(detail, fallback = "Something went wrong. Please try again.") {
  if (typeof detail === "string" && detail) return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }

  return fallback;
}

export function setStatus(element, message, kind = "") {
  if (!element) return;
  element.textContent = message;
  element.className = `status-msg ${kind}`.trim();
}

export function setHidden(element, hidden) {
  if (element) element.hidden = hidden;
}

export function initPasswordToggle() {
  const toggle = document.querySelector(".password-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const inputs = document.querySelectorAll(
      'input[name="password"], input[name="password_confirmation"]'
    );
    const shouldShow = inputs[0]?.type === "password";
    const label = inputs.length === 1 ? "password" : "passwords";

    inputs.forEach((input) => {
      input.type = shouldShow ? "text" : "password";
    });
    toggle.textContent = shouldShow ? "Hide" : "Show";
    toggle.setAttribute(
      "aria-label",
      `${shouldShow ? "Hide" : "Show"} ${label}`
    );
  });
}

export function updateHighlight(items, highlightedIndex) {
  items.forEach((item, index) => {
    item.classList.toggle("is-highlighted", index === highlightedIndex);
  });

  items[highlightedIndex]?.scrollIntoView({ block: "nearest" });
}

export function openDropdown(input, list) {
  list.classList.add("is-open");
  input.setAttribute("aria-expanded", "true");
}

export function closeDropdown(input, list) {
  list.classList.remove("is-open");
  input.setAttribute("aria-expanded", "false");
}

export function renderMessage(message, input, list) {
  const item = document.createElement("li");
  item.className = "entry-item is-empty";
  item.textContent = message;

  list.replaceChildren(item);
  openDropdown(input, list);
}

export function renderResults(words, list, input, onSelect) {
  if (!words.length) {
    renderMessage("No matches found.", input, list);
    return;
  }

  const items = words.map((word) => {
    const item = document.createElement("li");
    const label = document.createElement("div");

    item.className = "entry-item";
    item.dataset.word = word;
    item.setAttribute("role", "option");
    label.className = "entry-word";
    label.textContent = word;
    item.append(label);
    item.addEventListener("click", () => {
      onSelect(word);
      input.focus();
    });

    return item;
  });

  list.replaceChildren(...items);
  openDropdown(input, list);
}

export function selectWord(word, quantityInput, savedList) {
  const quantity = !quantityInput.disabled && quantityInput.value ? `${quantityInput.value} ` : "";
  const saved = savedList.value;
  savedList.value = saved ? `${saved}\n${quantity}${word}` : `${quantity}${word}`;
}
