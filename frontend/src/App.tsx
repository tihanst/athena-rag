import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import type { ChatMessage, UploadedFile } from "./types";
import { deleteFile, fetchFiles, sendChatMessage, uploadFile } from "./api";

function makeId() {
  return crypto.randomUUID();
}

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchFiles()
      .then(setFiles)
      .catch(() => {
        /* backend not reachable yet; ignore for the mock front end */
      });
  }, []);

  const handleFilesSelected = useCallback((incoming: FileList | File[]) => {
    const list = Array.from(incoming);
    for (const file of list) {
      const tempId = makeId();
      setFiles((prev) => [
        ...prev,
        { id: tempId, name: file.name, size: file.size, status: "uploading" },
      ]);
      uploadFile(file)
        .then((saved) => {
          setFiles((prev) =>
            prev.map((f) => (f.id === tempId ? saved : f)),
          );
        })
        .catch(() => {
          setFiles((prev) =>
            prev.map((f) => (f.id === tempId ? { ...f, status: "error" } : f)),
          );
        });
    }
  }, []);

  const handleRemoveFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
    deleteFile(id).catch(() => {
      /* best effort in mock mode */
    });
  }, []);

  const handleSend = useCallback(
    (content: string) => {
      const userMessage: ChatMessage = {
        id: makeId(),
        role: "user",
        content,
        createdAt: Date.now(),
      };
      const pendingId = makeId();
      const pendingMessage: ChatMessage = {
        id: pendingId,
        role: "assistant",
        content: "",
        createdAt: Date.now(),
        pending: true,
      };

      setMessages((prev) => [...prev, userMessage, pendingMessage]);
      setSending(true);

      sendChatMessage(content, [...messages, userMessage])
        .then((reply) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === pendingId
                ? { ...m, content: reply.content, pending: false }
                : m,
            ),
          );
        })
        .catch((err) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === pendingId
                ? {
                    ...m,
                    content: `Error reaching backend: ${err.message}`,
                    pending: false,
                  }
                : m,
            ),
          );
        })
        .finally(() => setSending(false));
    },
    [messages],
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-100">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((c) => !c)}
        files={files}
        onFilesSelected={handleFilesSelected}
        onRemoveFile={handleRemoveFile}
      />
      <ChatArea
        messages={messages}
        onSend={handleSend}
        sending={sending}
        fileCount={files.length}
      />
    </div>
  );
}

export default App;
