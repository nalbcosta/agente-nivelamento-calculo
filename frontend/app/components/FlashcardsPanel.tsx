"use client";

import { useState } from "react";
import type { FlashcardsResponse } from "../types";

type CardDecision = "memorized" | "review";

type Props = {
  result: FlashcardsResponse | null;
  sessionMemorized: string[];
  onMemorize: (concept: string) => void;
};

function CardSession({
  flashcards,
  onMemorize,
  llmSource,
}: {
  flashcards: FlashcardsResponse["flashcards"];
  onMemorize: (concept: string) => void;
  llmSource: string;
}) {
  const [cardIndex, setCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [decisions, setDecisions] = useState<Record<number, CardDecision>>({});

  const totalCards = flashcards.length;
  const reviewedCount = Object.keys(decisions).length;
  const memorizedCount = Object.values(decisions).filter((d) => d === "memorized").length;
  const allReviewed = reviewedCount === totalCards;
  const card = flashcards[cardIndex];

  function advance(newDecisions: Record<number, CardDecision>) {
    setFlipped(false);
    const remaining = flashcards.map((_, i) => i).filter((i) => !(i in newDecisions));
    if (remaining.length > 0) {
      setCardIndex(remaining[0]);
    }
  }

  function handleMemorized() {
    onMemorize(card.concept);
    const newDecisions = { ...decisions, [cardIndex]: "memorized" as CardDecision };
    setDecisions(newDecisions);
    advance(newDecisions);
  }

  function handleReviewLater() {
    const newDecisions = { ...decisions, [cardIndex]: "review" as CardDecision };
    setDecisions(newDecisions);
    advance(newDecisions);
  }

  if (allReviewed) {
    return (
      <div className="mt-4 space-y-4">
        <div className="rounded-2xl border border-zinc-200 bg-white/70 p-6 text-center">
          <p className="text-3xl">{memorizedCount === totalCards ? "🎉" : "🎯"}</p>
          <p className="mt-2 font-semibold text-zinc-900">Sessão concluída!</p>
          <p className="mt-1 text-sm text-zinc-600">
            <span className="font-medium text-emerald-700">{memorizedCount}</span> de{" "}
            <span className="font-medium">{totalCards}</span> conceito(s) memorizado(s) nesta rodada.
          </p>
        </div>

        <div className="rounded-2xl border border-zinc-200 bg-white/70 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Resultado por conceito
          </h3>
          <ul className="space-y-1.5">
            {flashcards.map((c, i) => (
              <li key={c.concept} className="flex items-center justify-between text-sm">
                <span className="text-zinc-700">{c.concept}</span>
                {decisions[i] === "memorized" ? (
                  <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700">
                    ✓ Memorizado
                  </span>
                ) : (
                  <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs text-amber-700">
                    🔄 Rever
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-center text-xs text-zinc-400">
          Clique em <strong>Gerar Flashcards</strong> para uma nova rodada com os conceitos
          restantes.
        </p>
        <p className="text-center font-mono text-xs text-zinc-400">llm_source: {llmSource}</p>
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      {/* Progress bar */}
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>
          Card {reviewedCount + 1} de {totalCards}
        </span>
        <span className="text-emerald-700">{memorizedCount} memorizado(s)</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-200">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-300"
          style={{ width: `${(reviewedCount / totalCards) * 100}%` }}
        />
      </div>

      {/* Flashcard */}
      <div className="min-h-[180px] rounded-2xl border border-zinc-200 bg-white/80 p-6 shadow-sm">
        <p className="mb-3 font-mono text-xs uppercase tracking-wider text-zinc-400">
          {card.concept}
        </p>
        <p className="text-base font-medium leading-6 text-zinc-900">{card.front}</p>

        {flipped ? (
          <div className="mt-4 border-t border-zinc-200 pt-4">
            <p className="text-sm leading-6 text-zinc-600">{card.back}</p>
          </div>
        ) : null}
      </div>

      {/* Action buttons */}
      {!flipped ? (
        <button
          type="button"
          onClick={() => setFlipped(true)}
          className="w-full rounded-xl border border-zinc-300 bg-white py-2.5 text-sm font-medium transition hover:bg-zinc-50"
        >
          Ver resposta
        </button>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={handleReviewLater}
            className="rounded-xl border border-zinc-300 bg-white py-2.5 text-sm font-medium transition hover:bg-zinc-50"
          >
            🔄 Rever depois
          </button>
          <button
            type="button"
            onClick={handleMemorized}
            className="rounded-xl bg-emerald-700 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800"
          >
            ✓ Memorizado
          </button>
        </div>
      )}

      <p className="text-center font-mono text-xs text-zinc-400">llm_source: {llmSource}</p>
    </div>
  );
}

export function FlashcardsPanel({ result, sessionMemorized, onMemorize }: Props) {
  if (!result) {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-3 py-16 text-center">
        <span className="text-5xl">🃏</span>
        <p className="max-w-xs text-sm leading-6 text-zinc-500">
          Configure seu perfil e clique em <strong>Gerar Flashcards</strong>.
        </p>
        {sessionMemorized.length > 0 ? (
          <p className="text-xs text-emerald-700">
            {sessionMemorized.length} conceito(s) já memorizado(s) e excluído(s) da próxima rodada.
          </p>
        ) : null}
      </div>
    );
  }

  if (result.flashcards.length === 0) {
    return (
      <div className="mt-6 flex flex-col items-center justify-center gap-4 py-16 text-center">
        <span className="text-5xl">🎉</span>
        <p className="font-semibold text-zinc-900">Todos os conceitos foram memorizados!</p>
        <p className="max-w-xs text-sm text-zinc-500">
          Clique em <strong>Gerar Flashcards</strong> para verificar se há novos conceitos.
        </p>
        {result.memorized_concepts.length > 0 ? (
          <div className="mt-1 flex flex-wrap justify-center gap-1.5">
            {result.memorized_concepts.map((c) => (
              <span
                key={c}
                className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700"
              >
                ✓ {c}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <CardSession
      key={result.flashcards.map((f) => f.concept).join("|")}
      flashcards={result.flashcards}
      onMemorize={onMemorize}
      llmSource={result.llm_source}
    />
  );
}
