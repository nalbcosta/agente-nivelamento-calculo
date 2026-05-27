"use client";

import { useState } from "react";
import type { ConsolidacaoResponse } from "../types";

type Props = {
  step: "idle" | "questions" | "diagnosed";
  questions: string[];
  result: ConsolidacaoResponse | null;
  onSubmitAnswers: (answers: string[]) => void;
  loading: boolean;
  error: string | null;
};

function AnswerForm({
  questions,
  onSubmit,
  loading,
}: {
  questions: string[];
  onSubmit: (answers: string[]) => void;
  loading: boolean;
}) {
  const [answers, setAnswers] = useState<string[]>(() => questions.map(() => ""));

  function handleChange(index: number, value: string) {
    setAnswers((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  const hasAnyAnswer = answers.some((a) => a.trim().length > 0);

  return (
    <div className="space-y-4">
      <p className="text-sm leading-6 text-zinc-600">
        Responda cada questão com suas próprias palavras — o agente usará suas respostas para
        diagnosticar o que você aprendeu.
      </p>
      {questions.map((question, i) => (
        <div
          key={i}
          className="space-y-2.5 rounded-2xl border border-zinc-200 bg-white/70 p-4"
        >
          <p className="text-sm font-medium text-zinc-800">
            <span className="mr-2 font-mono text-xs text-zinc-400">{i + 1}.</span>
            {question}
          </p>
          <textarea
            value={answers[i] ?? ""}
            onChange={(e) => handleChange(i, e.target.value)}
            placeholder="Sua resposta..."
            className="h-20 w-full resize-none rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm outline-none ring-emerald-500/40 focus:ring"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => onSubmit(answers)}
        disabled={loading || !hasAnyAnswer}
        className="w-full rounded-xl bg-emerald-700 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? "Analisando respostas..." : "Analisar meu aprendizado →"}
      </button>
    </div>
  );
}

function DiagnosisView({ result }: { result: ConsolidacaoResponse }) {
  return (
    <div className="space-y-5">
      <p className="font-mono text-xs text-zinc-400">llm_source: {result.llm_source}</p>

      {/* Objectives diagnosis — the diferencial */}
      <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white/70 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Diagnóstico de Objetivos de Conhecimento
        </h3>

        {result.dominated_objectives.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-emerald-700">✅ Dominados</p>
            <div className="flex flex-wrap gap-1.5">
              {result.dominated_objectives.map((o) => (
                <span
                  key={o}
                  className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700"
                >
                  {o}
                </span>
              ))}
            </div>
          </div>
        )}

        {result.partial_objectives.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-amber-700">⚠️ Parcialmente compreendidos</p>
            <div className="flex flex-wrap gap-1.5">
              {result.partial_objectives.map((o) => (
                <span
                  key={o}
                  className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs text-amber-700"
                >
                  {o}
                </span>
              ))}
            </div>
          </div>
        )}

        {result.not_understood_objectives.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-red-700">❌ Não compreendidos</p>
            <div className="flex flex-wrap gap-1.5">
              {result.not_understood_objectives.map((o) => (
                <span
                  key={o}
                  className="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-xs text-red-700"
                >
                  {o}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Review recommendation */}
      <section className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-blue-50/40 p-5">
        <p className="mb-2 font-mono text-xs uppercase tracking-[0.18em] text-indigo-600">
          📋 Recomendação de Revisão
        </p>
        <p className="text-sm leading-[1.75] text-zinc-800">{result.review_recommendation}</p>
      </section>

      {/* Questions used */}
      {result.consolidation_questions.length > 0 && (
        <details className="rounded-2xl border border-zinc-200 bg-white/50 p-4">
          <summary className="cursor-pointer select-none text-xs font-medium text-zinc-500 hover:text-zinc-700">
            Ver perguntas usadas ({result.consolidation_questions.length})
          </summary>
          <ol className="mt-3 list-decimal space-y-2 pl-5">
            {result.consolidation_questions.map((q, i) => (
              <li key={i} className="text-sm text-zinc-700">
                {q}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

export function ConsolidacaoPanel({
  step,
  questions,
  result,
  onSubmitAnswers,
  loading,
  error,
}: Props) {
  if (step === "idle" && !loading) {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-3 py-16 text-center">
        <span className="text-5xl">🎓</span>
        <p className="max-w-xs text-sm leading-6 text-zinc-500">
          Clique em <strong>Buscar Perguntas</strong> para o agente gerar as questões de
          consolidação da aula de Cálculo I.
        </p>
      </div>
    );
  }

  if (loading && step !== "diagnosed") {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-700" />
        <p className="text-sm text-zinc-500">
          {step === "questions" ? "Analisando respostas..." : "Gerando perguntas..."}
        </p>
      </div>
    );
  }

  if (error && step === "idle") {
    return (
      <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5 text-center">
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (step === "questions" && questions.length > 0) {
    return (
      <div className="mt-4">
        <AnswerForm
          key={questions.join("|")}
          questions={questions}
          onSubmit={onSubmitAnswers}
          loading={loading}
        />
      </div>
    );
  }

  if (step === "diagnosed" && result) {
    return (
      <div className="mt-4">
        <DiagnosisView result={result} />
      </div>
    );
  }

  return null;
}
