export interface Result {
    exam_id: number;
    exam_title: string;
    exam_scheduled_time_utc: string;
    total_marks_awarded: number;
    total_marks_possible: number;
    overall_status: 'Results Declared' | 'Pending Evaluation';
    questions: {
      question_id: number;
      question_text: string;
      question_type: string;
      your_response: string;
      submitted_at_utc: string;
      marks_awarded: number | null;
      marks_possible: number;
      feedback: string;
      evaluated_at_utc: string | null;
      evaluated_by: string | null;
      status: 'Evaluated' | 'Pending Evaluation';
    }[];
  }