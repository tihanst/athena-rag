export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  pending?: boolean;
}

export type UploadStatus = "uploading" | "ready" | "error" | "missing";

export interface UploadedFile {
  id: string;
  name: string;
  size?: number;
  status: UploadStatus;
}

export interface DocumentStatus {
  exists: string[];
  missing: string[];
}
