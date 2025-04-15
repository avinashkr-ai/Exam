export interface Question {
    id: number;
    exam_id: number;
    question_text: string;
    question_type: 'MCQ' | 'Short Answer' | 'Long Answer';
    options?: { [key: string]: string };
    correct_answer?: string;
    marks: number;
    word_limit?: number;
  }