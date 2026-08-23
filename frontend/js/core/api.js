export class ApiError extends Error {
  constructor(status, detail, data = {}) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

async function request(path, options = {}) {
  const { timeoutMs = 0, ...fetchOptions } = options;
  const controller = timeoutMs ? new AbortController() : null;
  const timeout = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;

  try {
    const response = await fetch(path, {
      ...fetchOptions,
      signal: controller?.signal ?? fetchOptions.signal,
    });
    const data = response.status === 204
      ? null
      : await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new ApiError(response.status, data?.detail, data);
    }

    return data;
  } finally {
    if (timeout !== null) window.clearTimeout(timeout);
  }
}

export function getCurrentUser() {
  return request("/users/me", { timeoutMs: 5000 });
}

export function authenticate(mode, email, password) {
  if (mode !== "login" && mode !== "register") {
    throw new TypeError(`Unsupported authentication mode: ${mode}`);
  }

  return request(`/users/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function requestPasswordReset(email) {
  return request("/users/password-reset/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token, password) {
  return request("/users/password-reset/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
}

export function logout() {
  return request("/users/logout", { method: "POST" });
}

export function searchEntries(prefix = "") {
  return request(`/search?prefix=${encodeURIComponent(prefix)}`);
}

export function insertEntry(word) {
  return request(`/insert?word=${encodeURIComponent(word)}`, {
    method: "POST",
  });
}

export function deleteEntry(word) {
  return request(`/delete?word=${encodeURIComponent(word)}`, {
    method: "DELETE",
  });
}

export function deleteAllEntries() {
  return request("/delete_all", { method: "DELETE" });
}

function csvFormData(file, column = "") {
  const formData = new FormData();
  formData.append("file", file);
  if (column) formData.append("column", column);

  return formData;
}

export function previewEntries(file, column) {
  return request("/insert_csv/preview", {
    method: "POST",
    body: csvFormData(file, column),
  });
}

export function uploadEntries(entries) {
  return request("/insert_csv", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries }),
  });
}
