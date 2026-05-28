import { AlertTriangle, BookOpen, CheckCircle, Sparkles, X } from "lucide-react";
import type { NivelamentoResponse } from "../types";
import MathText from "./MathText";

export function NivelamentoPanel({ result }: { result: NivelamentoResponse | null }) {
  if (!result) {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-4 py-16 text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl border border-zinc-200 bg-white shadow-sm">
          <BookOpen className="size-6 text-zinc-400" />
        </div>
        <p className="max-w-xs text-sm leading-6 text-zinc-500">
          Informe seu perfil e clique em <strong>Analisar Nivelamento</strong> para verificar se você
          está pronto para a aula de Cálculo I.
        </p>
      </div>
    );
  }

  const missingSet = new Set(result.missing_prerequisites);

  return (
    <div className="mt-4 space-y-4">
      {/* Readiness banner */}
      <div
        className={`flex items-start gap-3 rounded-2xl border p-4 ${
          result.is_ready
            ? "border-emerald-200 bg-emerald-50"
            : "border-amber-200 bg-amber-50"
        }`}
      >
        {result.is_ready ? (
          <CheckCircle className="mt-0.5 size-5 shrink-0 text-emerald-600" />
        ) : (
          <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-500" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-zinc-900">
            {result.is_ready
              ? "Você está pronto para a aula!"
              : "Revise alguns pré-requisitos antes de iniciar a aula"}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500">
            {result.missing_prerequisites.length === 0
              ? "Todos os pré-requisitos identificados."
              : `${result.missing_prerequisites.length} pré-requisito(s) a reforçar.`}
          </p>
        </div>
        <span className="shrink-0 rounded-md bg-white/60 px-2 py-0.5 font-mono text-xs text-zinc-400 border border-zinc-200">
          {result.llm_source}
        </span>
      </div>

      {/* Prerequisites vs lesson topics */}
      <div className="grid grid-cols-2 gap-3">
        <section className="rounded-2xl border border-zinc-200 bg-white/70 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Pré-requisitos da aula
          </h3>
          {result.extracted_prerequisites.length === 0 ? (
            <p className="text-xs text-zinc-400">Nenhum extraído.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.extracted_prerequisites.map((item) => (
                <li
                  key={item}
                  className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs ${
                    missingSet.has(item)
                      ? "bg-red-50 text-red-700"
                      : "bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {missingSet.has(item) ? (
                    <X className="size-3 shrink-0" />
                  ) : (
                    <CheckCircle className="size-3 shrink-0" />
                  )}
                  {item}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white/70 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Tópicos da aula
          </h3>
          {result.detected_lesson_topics.length === 0 ? (
            <p className="text-xs text-zinc-400">Nenhum detectado.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.detected_lesson_topics.map((item) => (
                <li
                  key={item}
                  className="rounded-lg bg-zinc-100 px-2.5 py-1.5 text-xs text-zinc-700"
                >
                  {item}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Conteúdo de Nivelamento / Reforço */}
      {result.support_text ? (
        <section className="rounded-2xl border border-blue-200 bg-linear-to-br from-blue-50 to-indigo-50/40 p-5">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles className="size-3.5 text-blue-500" />
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-blue-600">
              {result.is_ready ? "Reforço Recomendado" : "Conteúdo de Nivelamento"}
            </p>
          </div>
          <MathText text={result.support_text} className="text-sm leading-[1.8] text-zinc-800" />
        </section>
      ) : null}
    </div>
  );
}
