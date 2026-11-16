// The only file that talks to the Python server (server.py).
// Every function returns: { reply, tools_used, approval }

async function post(path, body) {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({})); // a crashed/offline server may not send JSON
  if (!res.ok) {
    throw new Error(data.detail || `Can't reach the library server (error ${res.status}). Check that server.py is running.`);
  }
  return data;
}

export const sendMessage = (sessionId, message) =>
  post("/chat", { session_id: sessionId, message });

export const answerApproval = (sessionId, approved) =>
  post("/confirm", { session_id: sessionId, approved });
