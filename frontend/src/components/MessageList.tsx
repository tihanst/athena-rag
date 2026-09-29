import { useEffect, useRef } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function Avatar({ role }: { role: ChatMessage["role"] }) {
  const isUser = role === "user";
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-semibold text-white ${
        isUser ? "bg-indigo-500" : "bg-emerald-600"
      }`}
    >
      {isUser ? "You" : "AI"}
    </div>
  );
}

function MessageContent({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700">
        {message.content}
      </p>
    );
  }

  return (
    <article className="prose prose-sm prose-slate mt-1 max-w-none break-words text-slate-700 prose-headings:text-slate-900 prose-p:my-2 prose-p:leading-relaxed prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline prose-pre:max-w-full prose-pre:overflow-x-auto prose-table:block prose-table:max-w-full prose-table:overflow-x-auto [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          // Do not let model-generated Markdown trigger third-party image requests.
          img: ({ alt = "" }) => (
            <span className="italic text-slate-500">
              {alt ? `[Image: ${alt}]` : "[Image omitted]"}
            </span>
          ),
        }}
      >
        {message.content}
      </Markdown>
    </article>
  );
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-1 flex-col items-center justify-center px-6 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50">
          <SparkleIcon className="h-7 w-7 text-indigo-500" />
        </div>
        <h2 className="text-lg font-semibold text-slate-800">
          Ask anything about your corpus
        </h2>
        <p className="mt-1 max-w-sm text-sm text-slate-500">
          Upload documents on the left, then start a conversation. Responses
          will be grounded in the files you provide.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-6">
        {messages.map((m) => (
          <div key={m.id} className="flex gap-3">
            <Avatar role={m.role} />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-semibold text-slate-900">
                  {m.role === "user" ? "You" : "Assistant"}
                </span>
                <span className="text-xs text-slate-400">
                  {formatTime(m.createdAt)}
                </span>
              </div>
              {m.pending ? (
                <div className="mt-1 flex items-center gap-1 text-slate-400">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                </div>
              ) : (
                <MessageContent message={m} />
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function SparkleIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path
        d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8-1.8-.7 1.8-.7L19 15z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}
