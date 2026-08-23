import { requestPasswordReset, resetPassword } from "../core/api.js";
import { formatError, setStatus } from "../core/ui.js";

function initPasswordToggle() {
  const toggle = document.querySelector(".password-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const inputs = document.querySelectorAll(
      'input[name="password"], input[name="password_confirmation"]'
    );
    const shouldShow = inputs[0]?.type === "password";

    inputs.forEach((input) => {
      input.type = shouldShow ? "text" : "password";
    });
    toggle.textContent = shouldShow ? "Hide" : "Show";
    toggle.setAttribute(
      "aria-label",
      shouldShow ? "Hide passwords" : "Show passwords"
    );
  });
}

function initResetRequestForm() {
  const form = document.getElementById("reset-request-form");
  const status = document.getElementById("auth-status");
  if (!form || !status) return;

  const submitButton = form.querySelector('button[type="submit"]');
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(status, "");
    if (!form.reportValidity()) return;

    submitButton.disabled = true;
    submitButton.textContent = "Sending…";
    const email = String(new FormData(form).get("email") || "").trim();

    try {
      const result = await requestPasswordReset(email);
      setStatus(status, result.message, "ok");
      form.reset();
    } catch (error) {
      setStatus(status, formatError(error.detail), "err");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Send reset link";
    }
  });
}

function initResetPasswordForm() {
  const form = document.getElementById("reset-password-form");
  const status = document.getElementById("auth-status");
  if (!form || !status) return;

  const token = new URLSearchParams(window.location.search).get("token");
  const submitButton = form.querySelector('button[type="submit"]');
  if (!token) {
    submitButton.disabled = true;
    setStatus(status, "This password reset link is invalid or incomplete.", "err");
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setStatus(status, "");
    if (!form.reportValidity()) return;

    const data = new FormData(form);
    const password = String(data.get("password") || "");
    const confirmation = String(data.get("password_confirmation") || "");
    if (password !== confirmation) {
      setStatus(status, "Passwords do not match.", "err");
      document.getElementById("password-confirmation")?.focus();
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Resetting…";

    try {
      await resetPassword(token, password);
      setStatus(status, "Password reset. Redirecting to log in…", "ok");
      window.setTimeout(() => window.location.replace("/login"), 900);
    } catch (error) {
      setStatus(status, formatError(error.detail), "err");
      submitButton.disabled = false;
      submitButton.textContent = "Reset password";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initPasswordToggle();
  initResetRequestForm();
  initResetPasswordForm();
});
