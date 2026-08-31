import { useRef, useState } from "react";
import type { DragEvent } from "react";
import type { UploadedFile } from "../types";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  files: UploadedFile[];
  onFilesSelected: (files: FileList | File[]) => void;
  onRemoveFile: (id: string) => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusBadge({ status }: { status: UploadedFile["status"] }) {
  if (status === "uploading") {
    return (
      <span className="flex items-center gap-1 text-xs text-amber-300">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-300" />
        Uploading
      </span>
    );
  }
  if (status === "error") {
    return <span className="text-xs text-red-400">Failed</span>;
  }
  if (status === "missing") {
    return (
      <span className="flex items-center gap-1 text-xs text-orange-400">
        <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
        Missing &ndash; needs re-upload
      </span>
    );
  }
  return <span className="text-xs text-emerald-400">Ready</span>;
}

export default function Sidebar({
  collapsed,
  onToggleCollapsed,
  files,
  onFilesSelected,
  onRemoveFile,
}: SidebarProps) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.length) {
      onFilesSelected(e.dataTransfer.files);
    }
  }

  if (collapsed) {
    return (
      <div className="flex h-full w-14 flex-col items-center gap-3 border-r border-slate-800 bg-slate-900 py-4">
        <button
          type="button"
          onClick={onToggleCollapsed}
          title="Expand sidebar"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <ChevronRightIcon />
        </button>
        <div className="mt-2 h-px w-8 bg-slate-800" />
        <button
          type="button"
          onClick={() => {
            onToggleCollapsed();
            requestAnimationFrame(() => inputRef.current?.click());
          }}
          title="Upload files"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <UploadIcon />
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full w-1/4 min-w-[240px] max-w-[360px] flex-col border-r border-slate-800 bg-slate-900 text-slate-100">
      <div className="relative flex items-center justify-between bg-[linear-gradient(to_bottom,rgba(99,102,241,0.35)_0%,transparent_30%,transparent_70%,rgba(99,102,241,0.35)_100%)] px-4 py-4">
        <div
          className="pointer-events-none absolute inset-0 opacity-50"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg%20xmlns%3D'http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg'%20width%3D'320'%20height%3D'320'%3E%3Cfilter%20id%3D'n'%3E%3CfeTurbulence%20type%3D'fractalNoise'%20baseFrequency%3D'2.5'%20numOctaves%3D'3'%20stitchTiles%3D'stitch'%20result%3D'noise'%2F%3E%3CfeColorMatrix%20in%3D'noise'%20type%3D'luminanceToAlpha'%20result%3D'alpha'%2F%3E%3CfeComponentTransfer%20in%3D'alpha'%20result%3D'alpha2'%3E%3CfeFuncA%20type%3D'linear'%20slope%3D'5'%20intercept%3D'-3.2'%2F%3E%3C%2FfeComponentTransfer%3E%3CfeFlood%20flood-color%3D'white'%20result%3D'white'%2F%3E%3CfeComposite%20in%3D'white'%20in2%3D'alpha2'%20operator%3D'in'%2F%3E%3C%2Ffilter%3E%3Crect%20width%3D'100%25'%20height%3D'100%25'%20filter%3D'url%28%23n%29'%2F%3E%3C%2Fsvg%3E\")",
            backgroundSize: "320px 320px",
          }}
        />
        <div className="flex items-center gap-2">
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white">
              RAG Portal
            </h1>
            <p className="text-xs text-slate-400">Knowledge corpus</p>
          </div>
          <div className="flex h-36 w-36 shrink-0 items-center justify-center">
            <img
              src="/Athena4_white.png"
              alt="RAG Portal logo"
              className="h-28 w-28 object-contain drop-shadow-[0_0_10px_rgba(129,140,248,0.45)]"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={onToggleCollapsed}
          title="Collapse sidebar"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <ChevronLeftIcon />
        </button>
      </div>

      <div className="flex flex-1 flex-col">
      <div className="mt-4 px-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${dragActive
            ? "border-indigo-400 bg-indigo-500/10"
            : "border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/60"
            }`}
        >
          <UploadIcon className="h-6 w-6 text-slate-400" />
          <p className="text-sm text-slate-300">
            <span className="font-medium text-indigo-400">
              Click to upload
            </span>{" "}
            or drag and drop
          </p>
          <p className="text-xs text-slate-500">
            PDF, TXT, MD, DOCX up to 25MB
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) onFilesSelected(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-4 pb-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Files ({files.length})
        </p>
        {files.length === 0 ? (
          <p className="text-sm text-slate-500">No files uploaded yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {files.map((f) => (
              <li
                key={f.id}
                className="group flex items-center gap-2 rounded-lg bg-slate-800/60 px-2.5 py-2"
              >
                <FileIcon className="h-4 w-4 shrink-0 text-slate-400" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-200" title={f.name}>
                    {f.name}
                  </p>
                  <div className="flex items-center gap-2">
                    {f.size !== undefined && (
                      <span className="text-xs text-slate-500">
                        {formatSize(f.size)}
                      </span>
                    )}
                    <StatusBadge status={f.status} />
                  </div>
                </div>
                {!f.id.startsWith("db-") && (
                  <button
                    type="button"
                    onClick={() => onRemoveFile(f.id)}
                    title="Remove file"
                    className="shrink-0 rounded p-1 text-slate-500 opacity-0 hover:bg-slate-700 hover:text-slate-200 group-hover:opacity-100"
                  >
                    <CloseIcon className="h-3.5 w-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      </div>
    </div>
  );
}

function ChevronLeftIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
      <path
        d="M12.5 15L7.5 10L12.5 5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
      <path
        d="M7.5 5L12.5 10L7.5 15"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function UploadIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M12 16V4m0 0L7 9m5-5l5 5M5 17v2a2 2 0 002 2h10a2 2 0 002-2v-2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FileIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M14 3v5h5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CloseIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
