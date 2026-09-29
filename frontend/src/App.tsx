import { useCallback, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import type { ChatMessage, UploadedFile } from "./types";
import {
  deleteFile,
  fetchFiles,
  fetchFilesStatus,
  sendChatMessage,
  uploadFile,
} from "./api";

function makeId() {
  return crypto.randomUUID();
}

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [chatViewKey, setChatViewKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadFiles() {
      setFilesLoading(true);

      // The in-memory file list resets on every backend restart, but the
      // database corpus persists. Fetch both sources together and merge them
      // by name so whichever request finishes last cannot overwrite the other.
      const [filesResult, statusResult] = await Promise.allSettled([
        fetchFiles(),
        fetchFilesStatus(),
      ]);

      if (cancelled) return;

      const loadedFiles = filesResult.status === "fulfilled" ? filesResult.value : [];
      const known = new Set(loadedFiles.map((file) => file.name));

      if (statusResult.status === "fulfilled") {
        for (const name of statusResult.value.exists) {
          if (!known.has(name)) {
            loadedFiles.push({ id: `db-exists-${name}`, name, status: "ready" });
            known.add(name);
          }
        }
        for (const name of statusResult.value.missing) {
          if (!known.has(name)) {
            loadedFiles.push({ id: `db-missing-${name}`, name, status: "missing" });
            known.add(name);
          }
        }
      }

      setFiles(loadedFiles);
      setFilesLoading(false);
    }

    void loadFiles();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const flushChatLog = () => {
      navigator.sendBeacon("/api/chat/reset");
    };

    // The backend is reset on pagehide, but browsers may restore this page's
    // React state from the back/forward cache. Clear that restored state and
    // remount the chat area so its independently managed draft is cleared too.
    const resyncOnRestore = (event: PageTransitionEvent) => {
      if (event.persisted) {
        setMessages([]);
        setSending(false);
        setChatViewKey((key) => key + 1);
      }
    };

    window.addEventListener("pagehide", flushChatLog);
    window.addEventListener("pageshow", resyncOnRestore);

    return () => {
      window.removeEventListener("pagehide", flushChatLog);
      window.removeEventListener("pageshow", resyncOnRestore);
    };
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

      sendChatMessage(content)
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
        filesLoading={filesLoading}
        onFilesSelected={handleFilesSelected}
        onRemoveFile={handleRemoveFile}
      />
      <ChatArea
        key={chatViewKey}
        messages={messages}
        onSend={handleSend}
        sending={sending}
        fileCount={files.length}
      />
    </div>
  );
}

export default App;
