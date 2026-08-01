import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-full items-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
      <div className="flex flex-1 items-end gap-2 rounded-2xl border border-slate-300 bg-white px-3 py-2 shadow-sm focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
          placeholder="Ask a question about your documents..."
          className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none disabled:opacity-60"
        />
      </div>
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        title="Send message"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        <SendIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

function SendIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M4 20l16-8L4 4v6l10 2-10 2v6z"
        fill="currentColor"
      />
    </svg>
  );
}
