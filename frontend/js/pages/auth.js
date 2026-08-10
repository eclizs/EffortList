import { authenticate, getCurrentUser } from "../core/api.js";
import { formatError, setStatus } from "../core/ui.js";

function initPasswordToggle() {
  const toggle = document.querySelector(".password-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const passwordInputs = document.querySelectorAll(
      'input[name="password"], input[name="password_confirmation"]'
    );
    const shouldShow = passwordInputs[0]?.type === "password";

    passwordInputs.forEach((input) => {
      input.type = shouldShow ? "text" : "password";
    });

    toggle.textContent = shouldShow ? "Hide" : "Show";
    toggle.setAttribute(
      "aria-label",
      shouldShow ? "Hide password" : "Show password"
    );
  });
}

async function redirectAuthenticatedUser() {
  try {
    await getCurrentUser();
    window.location.replace("/");
  } catch {
    // Guests remain on the authentication page.
  }
}

function initAuthForm() {
  const form = document.getElementById("auth-form");
  const status = document.getElementById("auth-status");
  if (!form || !status) return;

  const mode = form.dataset.mode;
  const submitButton = form.querySelector('button[type="submit"]');
  const defaultButtonText = submitButton.textContent;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(status, "");

    if (!form.reportValidity()) return;

    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");

    if (mode === "register") {
      const confirmation = String(formData.get("password_confirmation") || "");
      if (password !== confirmation) {
        setStatus(status, "Passwords do not match.", "err");
        document.getElementById("password-confirmation")?.focus();
        return;
      }
    }

    submitButton.disabled = true;
    submitButton.textContent = mode === "register"
      ? "Creating account…"
      : "Logging in…";

    try {
      await authenticate(mode, email, password);
      setStatus(
        status,
        mode === "register"
          ? "Account created."
          : "Logged in.",
        "ok"
      );
      window.location.replace("/");
    } catch (error) {
      setStatus(status, formatError(error.detail), "err");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = defaultButtonText;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  redirectAuthenticatedUser();
  initPasswordToggle();
  initAuthForm();
});
