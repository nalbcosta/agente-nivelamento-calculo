"use client";

import { AlertTriangle, CheckCircle, ChevronDown, ClipboardList, GraduationCap, Loader2, XCircle } from "lucide-react";
import { useState } from "react";
import type { ConsolidacaoResponse } from "../types";
import MathText from "./MathText";

type Props = {
  step: "idle" | "questions" | "diagnosed";
  questions: string[];
  result: ConsolidacaoResponse | null;
  onSubmitAnswers: (answers: string[]) => void;
  loading: boolean;
  error: string | null;
  submittedQuestions: string[];
  submittedAnswers: string[];
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
      <p className="text-sm leading-6 text-zinc-500">
        Responda cada questão com suas próprias palavras — o agente usará suas respostas para
        diagnosticar o que você aprendeu.
      </p>
      {questions.map((question, i) => (
        <div
          key={i}
          className="space-y-2.5 rounded-2xl border border-zinc-200 bg-white/70 p-4"
        >
          <p className="text-sm font-medium text-zinc-800">
            <span className="mr-2 inline-flex size-5 items-center justify-center rounded-full bg-zinc-100 font-mono text-xs text-zinc-500">
              {i + 1}
            </span>
            {question}
          </p>
          <textarea
            value={answers[i] ?? ""}
            onChange={(e) => handleChange(i, e.target.value)}
            placeholder="Sua resposta..."
            className="h-20 w-full resize-none rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => onSubmit(answers)}
        disabled={loading || !hasAnyAnswer}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Analisando respostas...
          </>
        ) : (
          "Analisar meu aprendizado"
        )}
      </button>
    </div>
  );
}

function DiagnosisView({
  result,
  submittedQuestions,
  submittedAnswers,
}: {
  result: ConsolidacaoResponse;
  submittedQuestions: string[];
  submittedAnswers: string[];
}) {
  const [questionsOpen, setQuestionsOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-400">Modelo: <span className="font-mono">{result.llm_source}</span></p>
      </div>

      {/* Objectives diagnosis */}
      <section className="space-y-3 rounded-2xl border border-zinc-200 bg-white/70 p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Diagnóstico de Objetivos
        </h3>

        {result.dominated_objectives.length > 0 && (
          <div>
            <div className="mb-2 flex items-center gap-1.5">
              <CheckCircle className="size-3.5 text-emerald-600" />
              <p className="text-xs font-medium text-emerald-700">Dominados</p>
            </div>
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
            <div className="mb-2 flex items-center gap-1.5">
              <AlertTriangle className="size-3.5 text-amber-500" />
              <p className="text-xs font-medium text-amber-700">Parcialmente compreendidos</p>
            </div>
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
            <div className="mb-2 flex items-center gap-1.5">
              <XCircle className="size-3.5 text-red-500" />
              <p className="text-xs font-medium text-red-700">Não compreendidos</p>
            </div>
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
      <section className="rounded-2xl border border-indigo-200 bg-linear-to-br from-indigo-50 to-blue-50/40 p-5">
        <div className="mb-3 flex items-center gap-2">
          <ClipboardList className="size-3.5 text-indigo-500" />
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-indigo-600">
            Recomendação de Revisão
          </p>
        </div>
        <MathText text={result.review_recommendation} className="text-sm leading-[1.75] text-zinc-800" />
      </section>

      {/* Questions + answers submitted by student */}
      {submittedQuestions.length > 0 && (
        <div className="rounded-2xl border border-zinc-200 bg-white/50">
          <button
            type="button"
            onClick={() => setQuestionsOpen((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-left"
          >
            <span className="text-xs font-medium text-zinc-500">
              Ver perguntas e respostas ({submittedQuestions.length})
            </span>
            <ChevronDown
              className={`size-4 text-zinc-400 transition-transform ${questionsOpen ? "rotate-180" : ""}`}
            />
          </button>
          {questionsOpen && (
            <ol className="list-decimal space-y-3 border-t border-zinc-200 px-4 pb-4 pt-3 pl-8">
              {submittedQuestions.map((q, i) => (
                <li key={i} className="space-y-1.5">
                  <p className="text-sm font-medium text-zinc-800">{q}</p>
                  {submittedAnswers[i]?.trim() ? (
                    <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
                      <p className="text-xs text-zinc-400 mb-0.5">Resposta do aluno</p>
                      <p className="text-sm text-zinc-700">{submittedAnswers[i]}</p>
                    </div>
                  ) : (
                    <p className="text-xs italic text-zinc-400">(sem resposta)</p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
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
  submittedQuestions,
  submittedAnswers,
}: Props) {
  if (step === "idle" && !loading) {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-4 py-16 text-center">
        <div className="flex size-14 items-center justify-center rounded-2xl border border-zinc-200 bg-white shadow-sm">
          <GraduationCap className="size-6 text-zinc-400" />
        </div>
        <p className="max-w-xs text-sm leading-6 text-zinc-500">
          Clique em <strong>Buscar Perguntas</strong> para o agente gerar as questões de
          consolidação da aula de Cálculo I.
        </p>
        {error && (
          <p className="max-w-xs rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">
            {error}
          </p>
        )}
      </div>
    );
  }

  if (loading && step !== "diagnosed") {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-3 py-16 text-center">
        <Loader2 className="size-8 animate-spin text-emerald-600" />
        <p className="text-sm text-zinc-500">
          {step === "questions" ? "Analisando respostas..." : "Gerando perguntas..."}
        </p>
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
        <DiagnosisView
          result={result}
          submittedQuestions={submittedQuestions}
          submittedAnswers={submittedAnswers}
        />
      </div>
    );
  }

  return null;
}


