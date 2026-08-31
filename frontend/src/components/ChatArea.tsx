import type { ChatMessage } from "../types";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

interface ChatAreaProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  sending: boolean;
  fileCount: number;
}

export default function ChatArea({
  messages,
  onSend,
  sending,
  fileCount,
}: ChatAreaProps) {
  return (
    <div className="flex h-full flex-1 flex-col bg-slate-50">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            Knowledge base chat
          </h2>
          <p className="text-xs text-slate-500">
            {fileCount > 0
              ? `${fileCount} file${fileCount === 1 ? "" : "s"} available for context`
              : "No files uploaded yet"}
          </p>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col">
        <MessageList messages={messages} />
      </div>

      <div className="h-[15%] min-h-[110px] max-h-[220px] shrink-0">
        <ChatInput onSend={onSend} disabled={sending} />
      </div>
    </div>
  );
}
