import type { ChatMessage, UploadedFile } from "./types";

const BASE = "/api";

async function parseOrThrow(res: Response) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
): Promise<{ role: "assistant"; content: string }> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history: history.map((m) => ({ role: m.role, content: m.content })),
    }),
  });
  return parseOrThrow(res);
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    body: form,
  });
  return parseOrThrow(res);
}

export async function fetchFiles(): Promise<UploadedFile[]> {
  const res = await fetch(`${BASE}/files`);
  return parseOrThrow(res);
}

export async function deleteFile(id: string): Promise<void> {
  const res = await fetch(`${BASE}/files/${id}`, { method: "DELETE" });
  await parseOrThrow(res);
}
