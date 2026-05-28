"use client";

import { X } from "lucide-react";
import { useRef, useState } from "react";

type Props = {
  value: string; // newline-separated list
  onChange: (value: string) => void;
  placeholder?: string;
};

export function TagInput({ value, onChange, placeholder }: Props) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const tags = value
    .split(/[\n,]+/)
    .map((t) => t.trim())
    .filter(Boolean);

  function addTag(raw: string) {
    const additions = raw
      .split(/[,\n]+/)
      .map((t) => t.trim())
      .filter(Boolean)
      .filter((t) => !tags.some((x) => x.toLowerCase() === t.toLowerCase()));
    if (!additions.length) {
      setInput("");
      return;
    }
    onChange([...tags, ...additions].join("\n"));
    setInput("");
  }

  function removeTag(index: number) {
    onChange(tags.filter((_, i) => i !== index).join("\n"));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (input.trim()) addTag(input);
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  }

  return (
    <div
      className="flex min-h-20 flex-wrap items-start gap-1.5 rounded-xl border border-zinc-200 bg-white px-3 py-2.5 cursor-text transition focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20"
      onClick={() => inputRef.current?.focus()}
    >
      {tags.map((tag, i) => (
        <span
          key={`${tag}-${i}`}
          className="inline-flex shrink-0 items-center gap-1 rounded-full border border-zinc-200 bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700"
        >
          {tag}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              removeTag(i);
            }}
            className="ml-0.5 text-zinc-400 transition hover:text-red-500"
          >
            <X className="size-2.5" />
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (input.trim()) addTag(input);
        }}
        placeholder={tags.length === 0 ? (placeholder ?? "Digite e pressione Enter") : ""}
        className="min-w-25 flex-1 bg-transparent text-sm text-zinc-900 outline-none placeholder:text-zinc-400"
      />
    </div>
  );
}
