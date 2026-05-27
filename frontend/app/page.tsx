"use client";

import { useEffect, useMemo, useState } from "react";

import { ConsolidacaoPanel } from "./components/ConsolidacaoPanel";
import { FlashcardsPanel } from "./components/FlashcardsPanel";
import { NivelamentoPanel } from "./components/NivelamentoPanel";
import {
  type ConsolidacaoResponse,
  type FlashcardsResponse,
  type Flow,
  flowLabels,
  type NivelamentoResponse,
} from "./types";

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
const sessionStorageKey = "agente_calculo_frontend_session_v2";
type Endpoint = "ingest" | Flow;

type EndpointState = {
  loading: boolean;
  error: string | null;
  success: string | null;
};

type SessionSnapshot = {
  flow: Flow;
  studentId: string;
  studentBackground: string;
  knownTopicsText: string;
  memorizedConceptsText: string;
  targetFlashcards: number;
};

function readSessionSnapshot(): SessionSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = localStorage.getItem(sessionStorageKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<SessionSnapshot>;
    return {
      flow:
        parsed.flow === "nivelamento" || parsed.flow === "consolidacao" || parsed.flow === "flashcards"
          ? parsed.flow
          : "nivelamento",
      studentId: typeof parsed.studentId === "string" ? parsed.studentId : "aluno_front_001",
      studentBackground:
        typeof parsed.studentBackground === "string"
          ? parsed.studentBackground
          : "Tenho base inicial em calculo, com mais seguranca em limites do que em regra da cadeia.",
      knownTopicsText: typeof parsed.knownTopicsText === "string" ? parsed.knownTopicsText : "Limites\nDerivada",
      memorizedConceptsText:
        typeof parsed.memorizedConceptsText === "string" ? parsed.memorizedConceptsText : "Limites",
      targetFlashcards:
        typeof parsed.targetFlashcards === "number" && Number.isFinite(parsed.targetFlashcards)
          ? Math.min(8, Math.max(1, Math.round(parsed.targetFlashcards)))
          : 3,
    };
  } catch {
    return null;
  }
}

function splitList(value: string): string[] {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function Home() {
  const snapshot = readSessionSnapshot();

  const [flow, setFlow] = useState<Flow>(snapshot?.flow ?? "nivelamento");
  const [studentId, setStudentId] = useState(snapshot?.studentId ?? "aluno_front_001");
  const [studentBackground, setStudentBackground] = useState(
    snapshot?.studentBackground ??
      "Tenho base inicial em calculo, com mais seguranca em limites do que em regra da cadeia.",
  );
  const [knownTopicsText, setKnownTopicsText] = useState(snapshot?.knownTopicsText ?? "Limites\nDerivada");
  const [memorizedConceptsText, setMemorizedConceptsText] = useState(
    snapshot?.memorizedConceptsText ?? "",
  );
  const [targetFlashcards, setTargetFlashcards] = useState(snapshot?.targetFlashcards ?? 3);

  const [consolidacaoStep, setConsolidacaoStep] = useState<"idle" | "questions" | "diagnosed">("idle");
  const [consolidacaoQuestions, setConsolidacaoQuestions] = useState<string[]>([]);
  const [sessionMemorized, setSessionMemorized] = useState<string[]>([]);

  const [endpointStates, setEndpointStates] = useState<Record<Endpoint, EndpointState>>({
    ingest: { loading: false, error: null, success: null },
    nivelamento: { loading: false, error: null, success: null },
    consolidacao: { loading: false, error: null, success: null },
    flashcards: { loading: false, error: null, success: null },
  });

  const [nivelamentoResult, setNivelamentoResult] = useState<NivelamentoResponse | null>(null);
  const [consolidacaoResult, setConsolidacaoResult] = useState<ConsolidacaoResponse | null>(null);
  const [flashcardsResult, setFlashcardsResult] = useState<FlashcardsResponse | null>(null);

  const commonPayload = useMemo(
    () => ({
      student_id: studentId.trim(),
      student_background: studentBackground.trim(),
      known_topics: splitList(knownTopicsText),
    }),
    [knownTopicsText, studentBackground, studentId],
  );

  useEffect(() => {
    const snap: SessionSnapshot = {
      flow,
      studentId,
      studentBackground,
      knownTopicsText,
      memorizedConceptsText,
      targetFlashcards,
    };
    localStorage.setItem(sessionStorageKey, JSON.stringify(snap));
  }, [flow, knownTopicsText, memorizedConceptsText, studentBackground, studentId, targetFlashcards]);

  function setEndpointLoading(endpoint: Endpoint, loading: boolean): void {
    setEndpointStates((current) => ({
      ...current,
      [endpoint]: {
        ...current[endpoint],
        loading,
        error: loading ? null : current[endpoint].error,
        success: loading ? null : current[endpoint].success,
      },
    }));
  }

  function setEndpointError(endpoint: Endpoint, error: string): void {
    setEndpointStates((current) => ({
      ...current,
      [endpoint]: {
        ...current[endpoint],
        loading: false,
        error,
        success: null,
      },
    }));
  }

  function setEndpointSuccess(endpoint: Endpoint, success: string): void {
    setEndpointStates((current) => ({
      ...current,
      [endpoint]: {
        ...current[endpoint],
        loading: false,
        error: null,
        success,
      },
    }));
  }

  async function ingestLesson() {
    setEndpointLoading("ingest", true);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/nivelamento/ingest`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`Falha na ingestao (${response.status})`);
      }
      setEndpointSuccess("ingest", "Aula ingerida com sucesso. Agora voce pode executar os 3 cases.");
    } catch (error) {
      setEndpointError("ingest", error instanceof Error ? error.message : "Erro inesperado na ingestao.");
    }
  }

  async function runFlow() {
    if (!commonPayload.student_id) {
      setEndpointError(flow, "Informe um student_id para continuar.");
      return;
    }

    setEndpointLoading(flow, true);

    try {
      if (flow === "nivelamento") {
        const response = await fetch(`${apiBaseUrl}/api/v1/nivelamento`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(commonPayload),
        });
        if (!response.ok) {
          throw new Error(`Falha no nivelamento (${response.status})`);
        }
        const data = (await response.json()) as NivelamentoResponse;
        setNivelamentoResult(data);
        setEndpointSuccess("nivelamento", "Nivelamento concluido com sucesso.");
        return;
      }

      if (flow === "consolidacao") {
        // Step 1: fetch questions with empty answers
        setConsolidacaoStep("idle");
        setConsolidacaoResult(null);
        setConsolidacaoQuestions([]);
        const response = await fetch(`${apiBaseUrl}/api/v1/consolidacao`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...commonPayload, answered_questions: [] }),
        });
        if (!response.ok) {
          throw new Error(`Falha na consolidacao (${response.status})`);
        }
        const data = (await response.json()) as ConsolidacaoResponse;
        setConsolidacaoQuestions(data.consolidation_questions);
        setConsolidacaoStep("questions");
        setEndpointSuccess(
          "consolidacao",
          `${data.consolidation_questions.length} pergunta(s) gerada(s). Responda no painel ao lado!`,
        );
        return;
      }

      const payload = {
        ...commonPayload,
        memorized_concepts: splitList(memorizedConceptsText),
        target_flashcards: targetFlashcards,
      };
      const response = await fetch(`${apiBaseUrl}/api/v1/flashcards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Falha nos flashcards (${response.status})`);
      }
      const data = (await response.json()) as FlashcardsResponse;
      setFlashcardsResult(data);
      setEndpointSuccess("flashcards", `${data.flashcards.length} flashcard(s) gerado(s).`);
    } catch (error) {
      setEndpointError(flow, error instanceof Error ? error.message : "Erro inesperado ao executar fluxo.");
    }
  }

  async function submitConsolidacaoAnswers(answers: string[]) {
    setEndpointLoading("consolidacao", true);
    try {
      const payload = {
        ...commonPayload,
        answered_questions: answers.filter((a) => a.trim()),
      };
      const response = await fetch(`${apiBaseUrl}/api/v1/consolidacao`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Falha na consolidacao (${response.status})`);
      const data = (await response.json()) as ConsolidacaoResponse;
      setConsolidacaoResult(data);
      setConsolidacaoStep("diagnosed");
      setEndpointSuccess("consolidacao", "Diagnóstico concluído.");
    } catch (error) {
      setEndpointError("consolidacao", error instanceof Error ? error.message : "Erro inesperado.");
    }
  }

  function handleMemorize(concept: string) {
    setSessionMemorized((prev) => [...new Set([...prev, concept])]);
    setMemorizedConceptsText((prev) => {
      const existing = splitList(prev);
      if (existing.map((s) => s.toLowerCase()).includes(concept.toLowerCase())) return prev;
      return [...existing, concept].join("\n");
    });
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fee8d6_0%,_#f7f2ea_48%,_#eef6f0_100%)] px-5 py-10 text-zinc-900">
      <main className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[1.1fr_1fr]">
        <section className="rounded-3xl border border-zinc-300/70 bg-white/80 p-6 shadow-[0_15px_40px_-20px_rgba(40,40,40,0.45)] backdrop-blur">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-emerald-700">Agente de IA</p>
          <h1 className="mt-3 text-4xl font-semibold leading-tight">
            Calculo I
            <br />
            Jornada do Aluno
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-600">
            Nivelamento pré-aula, consolidação pós-aula e memorização adaptativa por flashcards.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {(Object.keys(flowLabels) as Flow[]).map((flowOption) => (
              <button
                key={flowOption}
                type="button"
                onClick={() => setFlow(flowOption)}
                className={`rounded-xl border px-3 py-3 text-left text-sm transition ${
                  flow === flowOption
                    ? "border-emerald-700 bg-emerald-700 text-white"
                    : "border-zinc-300 bg-white/70 hover:border-zinc-500"
                }`}
              >
                {flowLabels[flowOption]}
              </button>
            ))}
          </div>

          <form
            className="mt-6 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void runFlow();
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm">
                <span className="font-medium text-zinc-700">ID do aluno</span>
                <input
                  value={studentId}
                  onChange={(event) => setStudentId(event.target.value)}
                  className="w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 outline-none ring-emerald-500/40 focus:ring"
                />
              </label>
              <label className="space-y-1.5 text-sm">
                <span className="font-medium text-zinc-700">Tópicos conhecidos</span>
                <textarea
                  value={knownTopicsText}
                  onChange={(event) => setKnownTopicsText(event.target.value)}
                  placeholder="Um por linha ou separados por vírgula"
                  className="h-20 w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 outline-none ring-emerald-500/40 focus:ring"
                />
              </label>
            </div>

            <label className="space-y-1.5 text-sm">
              <span className="font-medium text-zinc-700">Background do aluno</span>
              <textarea
                value={studentBackground}
                onChange={(event) => setStudentBackground(event.target.value)}
                className="h-28 w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 outline-none ring-emerald-500/40 focus:ring"
              />
            </label>

            {flow === "consolidacao" ? (
              <div className="rounded-xl border border-zinc-200 bg-zinc-50/60 px-4 py-3 text-xs text-zinc-500">
                As perguntas serão geradas pelo agente. Você responderá no painel ao lado.
              </div>
            ) : null}

            {flow === "flashcards" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium text-zinc-700">Conceitos memorizados</span>
                  <textarea
                    value={memorizedConceptsText}
                    onChange={(event) => setMemorizedConceptsText(event.target.value)}
                    placeholder="Automático após cada rodada"
                    className="h-24 w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 outline-none ring-emerald-500/40 focus:ring"
                  />
                  {sessionMemorized.length > 0 ? (
                    <p className="text-xs text-emerald-700">{sessionMemorized.length} conceito(s) já excluído(s) desta sessão</p>
                  ) : null}
                </label>
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium text-zinc-700">Quantidade de flashcards</span>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={targetFlashcards}
                    onChange={(event) => setTargetFlashcards(Math.min(8, Math.max(1, Number(event.target.value || "1"))))}
                    className="w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 outline-none ring-emerald-500/40 focus:ring"
                  />
                </label>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => void ingestLesson()}
                disabled={endpointStates.ingest.loading}
                className="rounded-xl border border-zinc-400 bg-white px-4 py-2 text-sm font-medium transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {endpointStates.ingest.loading ? "Ingerindo..." : "Ingerir Aula"}
              </button>
              <button
                type="submit"
                disabled={endpointStates[flow].loading}
                className="rounded-xl bg-emerald-700 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {endpointStates[flow].loading
                  ? "Processando..."
                  : flow === "nivelamento"
                    ? "Analisar Nivelamento"
                    : flow === "consolidacao"
                      ? consolidacaoStep !== "idle"
                        ? "Buscar Novas Perguntas"
                        : "Buscar Perguntas"
                      : "Gerar Flashcards"}
              </button>
            </div>
          </form>

          {endpointStates.ingest.error ? (
            <p className="mt-4 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
              Endpoint ingest: {endpointStates.ingest.error}
            </p>
          ) : null}
          {endpointStates.ingest.success ? (
            <p className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              Endpoint ingest: {endpointStates.ingest.success}
            </p>
          ) : null}

          {endpointStates[flow].error ? (
            <p className="mt-4 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
              Endpoint {flow}: {endpointStates[flow].error}
            </p>
          ) : null}
          {endpointStates[flow].success ? (
            <p className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              Endpoint {flow}: {endpointStates[flow].success}
            </p>
          ) : null}
        </section>

        <section className="overflow-y-auto rounded-3xl border border-zinc-300/70 bg-white/80 p-6 shadow-[0_15px_40px_-20px_rgba(40,40,40,0.45)] backdrop-blur">
          <div>
            <h2 className="text-lg font-semibold">{flowLabels[flow]}</h2>
            <p className="mt-0.5 font-mono text-xs text-zinc-400">
              {apiBaseUrl}/api/v1/{flow}
            </p>
          </div>

          {flow === "nivelamento" ? <NivelamentoPanel result={nivelamentoResult} /> : null}

          {flow === "consolidacao" ? (
            <ConsolidacaoPanel
              step={consolidacaoStep}
              questions={consolidacaoQuestions}
              result={consolidacaoResult}
              onSubmitAnswers={submitConsolidacaoAnswers}
              loading={endpointStates.consolidacao.loading}
              error={endpointStates.consolidacao.error}
            />
          ) : null}

          {flow === "flashcards" ? (
            <FlashcardsPanel
              result={flashcardsResult}
              sessionMemorized={sessionMemorized}
              onMemorize={handleMemorize}
            />
          ) : null}
        </section>
      </main>
    </div>
  );
}
