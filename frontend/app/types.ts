export type Flow = "nivelamento" | "consolidacao" | "flashcards";

export type NivelamentoResponse = {
  is_ready: boolean;
  extracted_prerequisites: string[];
  missing_prerequisites: string[];
  detected_lesson_topics: string[];
  retrieved_context: string[];
  support_text: string;
  llm_source: string;
};

export type ConsolidacaoResponse = {
  consolidation_questions: string[];
  dominated_objectives: string[];
  partial_objectives: string[];
  not_understood_objectives: string[];
  review_recommendation: string;
  retrieved_context: string[];
  llm_source: string;
};

export type FlashcardItem = {
  concept: string;
  front: string;
  back: string;
};

export type FlashcardsResponse = {
  flashcards: FlashcardItem[];
  memorized_concepts: string[];
  remaining_concepts: string[];
  retrieved_context: string[];
  llm_source: string;
};

export type StudentProfile = {
  student_id: string;
  background: string | null;
  known_topics: string[];
  memorized_concepts: string[];
  previous_consolidation_questions: string[];
};

export const flowLabels: Record<Flow, string> = {
  nivelamento: "Case 1 - Nivelamento",
  consolidacao: "Case 2 - Consolidação",
  flashcards: "Case 3 - Flashcards",
};
