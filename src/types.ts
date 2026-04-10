export type QuestionType = 'A-E' | 'A-D-N' | 'Custom';

export interface QuestionConfig {
  id: number;
  type: QuestionType;
  options: string[];
  /** Single string for one-answer questions, or string[] for multi-answer questions. */
  correctAnswer?: string | string[];
  points: number;
}

export interface ExamTemplate {
  id: string;
  name: string;
  questions: QuestionConfig[];
  multiMarkQuestionIds?: number[];
  layout: {
    columns: number;
    questionsPerColumn: number;
  };
}

/** Answer key — mirrors omr_engine.models.AnswerKey. */
export interface AnswerKey {
  id: string;
  name: string;
  templateId: string;
  answers: Array<{
    questionId: number;
    /** 1+ items; 2+ for multi-answer questions. */
    options: string[];
    points: number;
  }>;
}

/** Selected answers for one student, keyed by question ID.
 *  Always an array so single- and multi-answer questions are handled uniformly. */
export type AnswerSelection = Record<number, string[]>;

export interface ScoredQuestion {
  questionId: number;
  expected: string[];
  selected: string[];
  isCorrect: boolean;
  isPartial: boolean;
  pointsEarned: number;
  pointsPossible: number;
  hasAmbiguous: boolean;
}

export interface ScanResult {
  studentId: string | null;
  studentName: string | null;
  answers: AnswerSelection;
  totalPoints: number;
  pointsPossible: number;
  percentage: number;
  correctCount: number;
  wrongCount: number;
  partialCount: number;
  wrongQuestionIds: number[];
  ambiguousQuestionIds: number[];
  questions: ScoredQuestion[];
}
