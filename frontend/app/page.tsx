"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ArrowRight, BrainCircuit, CheckCircle2, Info, Lock, Loader2, Upload } from "lucide-react";

import { ConsolidacaoPanel } from "./components/ConsolidacaoPanel";
import { FlashcardsPanel } from "./components/FlashcardsPanel";
import { NivelamentoPanel } from "./components/NivelamentoPanel";
import { TagInput } from "./components/TagInput";
import {
  type ConsolidacaoResponse,
  type FlashcardsResponse,
  type Flow,
  flowLabels,
  type NivelamentoResponse,
  type StudentProfile,
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

type Toast = { id: string; message: string; type: "success" | "error" };

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
  const [consolidacaoAnswers, setConsolidacaoAnswers] = useState<string[]>([]);
  const [sessionMemorized, setSessionMemorized] = useState<string[]>([]);
  const [completedSteps, setCompletedSteps] = useState<Set<Flow>>(new Set());
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [lastFetchedStudentId, setLastFetchedStudentId] = useState<string | null>(null);

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

  // Re-fetch profile whenever studentId changes
  useEffect(() => {
    const id = studentId.trim();
    if (!id || id === lastFetchedStudentId) return;
    setLastFetchedStudentId(id);
    setStudentProfile(null);
    fetch(`${apiBaseUrl}/api/v1/students/${encodeURIComponent(id)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data: StudentProfile | null) => {
        if (!data) return;
        setStudentProfile(data);

        const loaded: string[] = [];

        // Merge known_topics from DB
        if (data.known_topics?.length) {
          setKnownTopicsText((prev) => {
            const existing = new Set(
              prev.split(/\n|,/).map((s) => s.trim().toLowerCase()).filter(Boolean),
            );
            const toAdd = data.known_topics.filter((t) => !existing.has(t.toLowerCase()));
            if (!toAdd.length) return prev;
            return [
              ...(prev ? prev.split(/\n|,/).map((s) => s.trim()).filter(Boolean) : []),
              ...toAdd,
            ].join("\n");
          });
          loaded.push(`${data.known_topics.length} tópico(s) conhecido(s)`);
        }

        // Load background from DB if available
        if (data.background) {
          setStudentBackground(data.background);
          loaded.push("background");
        }

        // Merge memorized_concepts from DB
        if (data.memorized_concepts?.length) {
          setMemorizedConceptsText((prev) => {
            const existing = new Set(
              prev.split(/\n|,/).map((s) => s.trim().toLowerCase()).filter(Boolean),
            );
            const toAdd = data.memorized_concepts.filter((c) => !existing.has(c.toLowerCase()));
            if (!toAdd.length) return prev;
            return [
              ...(prev ? prev.split(/\n|,/).map((s) => s.trim()).filter(Boolean) : []),
              ...toAdd,
            ].join("\n");
          });
          loaded.push(`${data.memorized_concepts.length} conceito(s) memorizado(s)`);
        }

        if (loaded.length > 0) {
          showToast(`Perfil carregado: ${loaded.join(", ")}`, "success");
        }
      })
      .catch(() => undefined);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId, lastFetchedStudentId]);

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

  function showToast(message: string, type: "success" | "error" = "success") {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  }

  function setEndpointError(endpoint: Endpoint, error: string): void {
    setEndpointStates((current) => ({
      ...current,
      [endpoint]: { ...current[endpoint], loading: false, error, success: null },
    }));
    showToast(error, "error");
  }

  function setEndpointSuccess(endpoint: Endpoint, success: string): void {
    setEndpointStates((current) => ({
      ...current,
      [endpoint]: { ...current[endpoint], loading: false, error: null, success },
    }));
    showToast(success);
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

    // Reset consolidacao state when starting fresh
    if (flow === "consolidacao") {
      setConsolidacaoStep("idle");
      setConsolidacaoResult(null);
      setConsolidacaoQuestions([]);
      setConsolidacaoAnswers([]);
    }

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
        setCompletedSteps((prev) => new Set([...prev, "nivelamento"]));
        setEndpointSuccess("nivelamento", "Nivelamento concluido com sucesso.");
        return;
      }

      if (flow === "consolidacao") {
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
      setCompletedSteps((prev) => new Set([...prev, "flashcards"]));
      setEndpointSuccess("flashcards", `${data.flashcards.length} flashcard(s) gerado(s).`);
    } catch (error) {
      setEndpointError(flow, error instanceof Error ? error.message : "Erro inesperado ao executar fluxo.");
    }
  }

  async function submitConsolidacaoAnswers(answers: string[]) {
    setConsolidacaoAnswers(answers);
    setEndpointLoading("consolidacao", true);
    try {
      const payload = {
        ...commonPayload,
        consolidation_questions: consolidacaoQuestions,
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
      setCompletedSteps((prev) => new Set([...prev, "consolidacao"]));
      setEndpointSuccess("consolidacao", "Diagnóstico concluído.");
      // Re-fetch profile to show updated question history count
      setLastFetchedStudentId(null);
    } catch (error) {
      setEndpointError("consolidacao", error instanceof Error ? error.message : "Erro inesperado.");
    }
  }

  async function runFlashcardsReview() {
    setEndpointLoading("flashcards", true);
    try {
      const payload = {
        ...commonPayload,
        memorized_concepts: splitList(memorizedConceptsText),
        target_flashcards: targetFlashcards,
        review_mode: true,
      };
      const response = await fetch(`${apiBaseUrl}/api/v1/flashcards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`Falha nos flashcards (${response.status})`);
      const data = (await response.json()) as FlashcardsResponse;
      setFlashcardsResult(data);
      setEndpointSuccess("flashcards", `${data.flashcards.length} flashcard(s) de revisão gerado(s).`);
    } catch (error) {
      setEndpointError("flashcards", error instanceof Error ? error.message : "Erro inesperado.");
    }
  }

  function handleMemorize(concept: string) {
    setSessionMemorized((prev) => [...new Set([...prev, concept])]);
    setMemorizedConceptsText((prev) => {
      const existing = splitList(prev);
      if (existing.map((s) => s.toLowerCase()).includes(concept.toLowerCase())) return prev;
      return [...existing, concept].join("\n");
    });
    // Optimistically update the local profile badge
    setStudentProfile((prev) =>
      prev
        ? {
            ...prev,
            memorized_concepts: prev.memorized_concepts.includes(concept)
              ? prev.memorized_concepts
              : [...prev.memorized_concepts, concept],
          }
        : prev,
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fee8d6_0%,#f7f2ea_48%,#eef6f0_100%)] px-5 py-10 text-zinc-900">
      {/* Toast overlay */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex max-w-sm items-start gap-2.5 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-right-4 fade-in duration-300 ${
              toast.type === "success"
                ? "border-emerald-200 bg-emerald-50/95 text-emerald-800"
                : "border-red-200 bg-red-50/95 text-red-800"
            }`}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
            ) : (
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-red-500" />
            )}
            <p className="text-sm leading-5">{toast.message}</p>
          </div>
        ))}
      </div>
      <main className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[1.15fr_1fr]">
        {/* ── Left panel: controls ─────────────────────────────────── */}
        <section className="rounded-3xl border border-zinc-300/70 bg-white/80 p-7 shadow-[0_15px_40px_-20px_rgba(40,40,40,0.35)] backdrop-blur">
          <div className="flex items-center gap-2.5">
            <BrainCircuit className="size-5 text-emerald-700" />
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-emerald-700">Agente de IA</p>
          </div>
          <h1 className="mt-3 text-4xl font-semibold leading-tight tracking-tight">
            Cálculo I
            <br />
            Jornada do Aluno
          </h1>
          <p className="mt-2.5 max-w-2xl text-sm leading-6 text-zinc-500">
            Nivelamento pré-aula, consolidação pós-aula e memorização adaptativa por flashcards.
          </p>

          {/* Flow tabs */}

          {/* Student profile badge */}
          {studentProfile && (
            <div className="mt-4 flex flex-wrap gap-2">
              {studentProfile.known_topics.length > 0 && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs text-indigo-700">
                  <span className="size-1.5 rounded-full bg-indigo-400" />
                  {studentProfile.known_topics.length} tópico(s) no perfil
                </span>
              )}
              {studentProfile.memorized_concepts.length > 0 && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  {studentProfile.memorized_concepts.length} conceito(s) memorizados
                </span>
              )}
              {studentProfile.previous_consolidation_questions.length > 0 && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs text-blue-700">
                  <span className="size-1.5 rounded-full bg-blue-400" />
                  {studentProfile.previous_consolidation_questions.length} pergunta(s) no histórico
                </span>
              )}
              {studentProfile.known_topics.length === 0 &&
                studentProfile.memorized_concepts.length === 0 &&
                studentProfile.previous_consolidation_questions.length === 0 && (
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs text-zinc-500">
                    <span className="size-1.5 rounded-full bg-zinc-300" />
                    Aluno novo — sem histórico
                  </span>
                )}
            </div>
          )}

          {/* Sequential stepper */}
          <div className="mt-5 flex items-center gap-1">
            {(["nivelamento", "consolidacao", "flashcards"] as Flow[]).map((flowOption, idx) => {
              const isDone = completedSteps.has(flowOption);
              const isActive = flow === flowOption;
              const prerequisite: Flow | null = flowOption === "consolidacao" ? "nivelamento" : flowOption === "flashcards" ? "consolidacao" : null;
              const isLocked = prerequisite !== null && !completedSteps.has(prerequisite);
              return (
                <div key={flowOption} className="flex items-center gap-1 flex-1 min-w-0">
                  <button
                    type="button"
                    onClick={() => setFlow(flowOption)}
                    title={isLocked ? `Complete o Nivelamento primeiro` : undefined}
                    className={`flex min-w-0 flex-1 items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium transition ${
                      isActive
                        ? "border-emerald-700 bg-emerald-700 text-white shadow-sm"
                        : isDone
                          ? "border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                          : isLocked
                            ? "border-zinc-200 bg-zinc-50 text-zinc-400 cursor-not-allowed opacity-70"
                            : "border-zinc-200 bg-white/60 text-zinc-600 hover:border-zinc-400 hover:bg-white"
                    }`}
                  >
                    <span className={`flex size-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      isActive ? "bg-white/20 text-white" : isDone ? "bg-emerald-600 text-white" : isLocked ? "bg-zinc-200 text-zinc-400" : "bg-zinc-100 text-zinc-500"
                    }`}>
                      {isDone ? <CheckCircle2 className="size-3.5" /> : isLocked ? <Lock className="size-3" /> : idx + 1}
                    </span>
                    <span className="truncate">{flowLabels[flowOption]}</span>
                  </button>
                  {idx < 2 && (
                    <ArrowRight className={`size-3.5 shrink-0 ${completedSteps.has(flowOption) ? "text-emerald-400" : "text-zinc-300"}`} />
                  )}
                </div>
              );
            })}
          </div>

          <form
            className="mt-6 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void runFlow();
            }}
          >
            {/* Student ID + Known Topics */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  ID do aluno
                </label>
                <input
                  value={studentId}
                  onChange={(event) => setStudentId(event.target.value)}
                  placeholder="ex: aluno_001"
                  className="w-full rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  Tópicos conhecidos
                </label>
                <TagInput
                  value={knownTopicsText}
                  onChange={setKnownTopicsText}
                  placeholder="Digite um tópico e pressione Enter ou vírgula"
                />
              </div>
            </div>

            {/* Background */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                Background do aluno
              </label>
              <textarea
                value={studentBackground}
                onChange={(event) => setStudentBackground(event.target.value)}
                placeholder="Descreva seu nível atual e experiências com Cálculo..."
                rows={4}
                className="w-full resize-none rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>

            {flow === "consolidacao" ? (
              <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 text-xs text-zinc-500">
                As perguntas serão geradas pelo agente. Você responderá no painel ao lado.
              </div>
            ) : null}

            {flow === "flashcards" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Conceitos memorizados
                  </label>
                  <TagInput
                    value={memorizedConceptsText}
                    onChange={setMemorizedConceptsText}
                    placeholder="Preenchido automaticamente após cada rodada"
                  />
                  {sessionMemorized.length > 0 ? (
                    <p className="text-xs text-emerald-700">
                      {sessionMemorized.length} conceito(s) excluído(s) desta sessão
                    </p>
                  ) : null}
                </div>
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Quantidade de flashcards
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    value={targetFlashcards}
                    onChange={(event) =>
                      setTargetFlashcards(Math.min(8, Math.max(1, Number(event.target.value || "1"))))
                    }
                    className="w-full rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                  />
                  <p className="text-xs text-zinc-400">Entre 1 e 8 cards por rodada</p>
                </div>
              </div>
            ) : null}

            {/* Leveraged knowledge info */}
            {flow === "nivelamento" && studentProfile && (studentProfile.known_topics.length > 0 || studentProfile.background) && (
              <div className="flex items-start gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 px-3.5 py-2.5 text-xs text-indigo-700">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>
                  Aproveitando do perfil:{" "}
                  {[
                    studentProfile.known_topics.length > 0 && `${studentProfile.known_topics.length} tópico(s) conhecido(s)`,
                    studentProfile.background && "background cadastrado",
                  ].filter(Boolean).join(" e ")}
                </span>
              </div>
            )}

            {flow === "consolidacao" && studentProfile && studentProfile.previous_consolidation_questions.length > 0 && (
              <div className="flex items-start gap-2 rounded-xl border border-blue-200 bg-blue-50/60 px-3.5 py-2.5 text-xs text-blue-700">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>
                  Histórico de {studentProfile.previous_consolidation_questions.length} pergunta(s) salvas sendo considerado pelo agente.
                </span>
              </div>
            )}

            {flow === "flashcards" && studentProfile && studentProfile.memorized_concepts.length > 0 && (
              <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50/60 px-3.5 py-2.5 text-xs text-emerald-700">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>
                  {studentProfile.memorized_concepts.length} conceito(s) já memorizado(s) no perfil serão excluídos da nova rodada.
                </span>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex flex-wrap gap-3 pt-1">
              <button
                type="button"
                onClick={() => void ingestLesson()}
                disabled={endpointStates.ingest.loading}
                className="flex items-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {endpointStates.ingest.loading ? (
                  <Loader2 className="size-4 animate-spin text-zinc-400" />
                ) : (
                  <Upload className="size-4 text-zinc-400" />
                )}
                {endpointStates.ingest.loading ? "Ingerindo..." : "Ingerir Aula"}
              </button>
              <button
                type="submit"
                disabled={endpointStates[flow].loading}
                className="flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {endpointStates[flow].loading && (
                  <Loader2 className="size-4 animate-spin" />
                )}
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
        </section>

        {/* ── Right panel: results ──────────────────────────────────── */}
        <section className="overflow-y-auto rounded-3xl border border-zinc-300/70 bg-white/80 p-7 shadow-[0_15px_40px_-20px_rgba(40,40,40,0.35)] backdrop-blur">
          <div className="border-b border-zinc-100 pb-4">
            <h2 className="text-lg font-semibold text-zinc-900">{flowLabels[flow]}</h2>
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
              submittedQuestions={consolidacaoQuestions}
              submittedAnswers={consolidacaoAnswers}
            />
          ) : null}

          {flow === "flashcards" ? (
            <FlashcardsPanel
              result={flashcardsResult}
              sessionMemorized={sessionMemorized}
              onMemorize={handleMemorize}
              onReviewAll={runFlashcardsReview}
            />
          ) : null}

          {/* Próximo passo CTA */}
          {flow === "nivelamento" && completedSteps.has("nivelamento") && !completedSteps.has("consolidacao") && (
            <div className="mt-4 flex items-center justify-between rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
              <p className="text-sm text-emerald-800">
                <strong>Nivelamento concluído!</strong> Agora consolide o aprendizado pós-aula.
              </p>
              <button
                type="button"
                onClick={() => setFlow("consolidacao")}
                className="ml-3 flex shrink-0 items-center gap-1.5 rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-800"
              >
                Consolidação <ArrowRight className="size-3.5" />
              </button>
            </div>
          )}

          {flow === "consolidacao" && completedSteps.has("consolidacao") && !completedSteps.has("flashcards") && (
            <div className="mt-4 flex items-center justify-between rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3">
              <p className="text-sm text-blue-800">
                <strong>Diagnóstico concluído!</strong> Agora reforce com flashcards adaptativos.
              </p>
              <button
                type="button"
                onClick={() => setFlow("flashcards")}
                className="ml-3 flex shrink-0 items-center gap-1.5 rounded-xl bg-blue-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-blue-800"
              >
                Flashcards <ArrowRight className="size-3.5" />
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
