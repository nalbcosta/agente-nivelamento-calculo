"use client";

import katex from "katex";
import React from "react";

/** Split a string into alternating plain-text and math segments.
 *  Handles $$ ... $$ (display) and $ ... $ (inline) delimiters. */
function splitMath(
  text: string,
): Array<{ type: "text" | "display" | "inline"; content: string }> {
  const segments: Array<{ type: "text" | "display" | "inline"; content: string }> = [];
  // Match $$ first (display), then $ (inline)
  const re = /(\$\$[\s\S]*?\$\$|\$[^\$\n]+?\$)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    const raw = match[0];
    if (raw.startsWith("$$")) {
      segments.push({ type: "display", content: raw.slice(2, -2).trim() });
    } else {
      segments.push({ type: "inline", content: raw.slice(1, -1).trim() });
    }
    lastIndex = match.index + raw.length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }

  return segments;
}

function renderKatex(latex: string, display: boolean): string {
  try {
    return katex.renderToString(latex, {
      displayMode: display,
      throwOnError: false,
      output: "htmlAndMathml",
    });
  } catch {
    return `<span class="text-red-500 font-mono text-xs">${latex}</span>`;
  }
}

/** Render a plain-text segment with **bold** and * bullet support */
function PlainSegment({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, li) => {
        const isBullet = /^\s*[\*\-]\s/.test(line);
        const stripped = isBullet ? line.replace(/^\s*[\*\-]\s/, "") : line;
        // Split on **bold**
        const parts = stripped.split(/(\*\*[^*]+\*\*)/g);
        const rendered = parts.map((part, pi) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={pi} className="font-semibold">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <React.Fragment key={pi}>{part}</React.Fragment>;
        });

        if (isBullet) {
          return (
            <li key={li} className="ml-4 list-disc">
              {rendered}
            </li>
          );
        }
        // Empty line = paragraph break
        if (!line.trim() && li > 0) {
          return <br key={li} />;
        }
        return <React.Fragment key={li}>{rendered}</React.Fragment>;
      })}
    </>
  );
}

interface MathTextProps {
  text: string;
  className?: string;
  /** Wrap bullet items in a <ul>. Default true */
  asList?: boolean;
}

/**
 * Renders text that may contain:
 * - $$ ... $$ display math blocks
 * - $ ... $ inline math
 * - **bold** markdown
 * - * or - bullet lists
 */
export default function MathText({ text, className, asList = true }: MathTextProps) {
  const segments = splitMath(text);

  const children = segments.map((seg, i) => {
    if (seg.type === "display") {
      return (
        <div
          key={i}
          className="my-2 overflow-x-auto"
          dangerouslySetInnerHTML={{ __html: renderKatex(seg.content, true) }}
        />
      );
    }
    if (seg.type === "inline") {
      return (
        <span
          key={i}
          dangerouslySetInnerHTML={{ __html: renderKatex(seg.content, false) }}
        />
      );
    }
    return <PlainSegment key={i} text={seg.content} />;
  });

  if (asList) {
    // Wrap everything in a container; <li> elements within PlainSegment need a <ul>
    return (
      <div className={className}>
        <ul className="space-y-0.5">{children}</ul>
      </div>
    );
  }

  return <span className={className}>{children}</span>;
}
