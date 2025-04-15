import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Question } from '../../../core/models/question';
import { ApiService } from '../../../core/services/api.service';

@Component({
  selector: 'app-question-management',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './question-management.component.html'
})
export class QuestionManagementComponent implements OnInit {
  examId: number;
  questions: Question[] = [];
  newQuestion: Partial<Question> = {
    question_text: '',
    question_type: 'MCQ',
    marks: 1,
    options: { A: '', B: '', C: '', D: '' },
    correct_answer: 'A'
  };
  editQuestion: Question | null = null;
  error: string | null = null;

  constructor(
    private examService: ApiService,
    private route: ActivatedRoute
  ) {
    this.examId = +this.route.snapshot.paramMap.get('id')!;
  }

  ngOnInit() {
    this.loadQuestions();
  }

  loadQuestions() {
    this.examService.getQuestions(this.examId).subscribe({
      next: (questions) => {
        this.questions = questions;
        console.log('Questions loaded:', questions);
      },
      error: (err) => {
        this.error = 'Failed to load questions.';
        console.error('Error loading questions:', err);
      }
    });
  }

  addQuestion() {
    if (!this.newQuestion.question_text || this.newQuestion.marks! <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    if (this.newQuestion.question_type === 'MCQ' && (!this.newQuestion.options || !this.newQuestion.correct_answer)) {
      this.error = 'MCQ requires options and correct answer.';
      return;
    }
    if (this.newQuestion.question_type !== 'MCQ') {
      this.newQuestion.options = undefined;
      this.newQuestion.correct_answer = undefined;
    }
    this.examService.addQuestion(this.examId, this.newQuestion).subscribe({
      next: () => {
        this.newQuestion = {
          question_text: '',
          question_type: 'MCQ',
          marks: 1,
          options: { A: '', B: '', C: '', D: '' },
          correct_answer: 'A'
        };
        this.loadQuestions();
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to add question.';
        console.error('Error adding question:', err);
      }
    });
  }

  startEdit(question: Question) {
    this.editQuestion = { ...question };
    if (!this.editQuestion.options) {
      this.editQuestion.options = { A: '', B: '', C: '', D: '' };
    }
  }

  updateQuestion() {
    if (!this.editQuestion || !this.editQuestion.question_text || this.editQuestion.marks <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    if (this.editQuestion.question_type === 'MCQ' && (!this.editQuestion.options || !this.editQuestion.correct_answer)) {
      this.error = 'MCQ requires options and correct answer.';
      return;
    }
    if (this.editQuestion.question_type !== 'MCQ') {
      this.editQuestion.options = undefined;
      this.editQuestion.correct_answer = undefined;
    }
    this.examService.updateQuestion(this.examId, this.editQuestion.id, this.editQuestion).subscribe({
      next: () => {
        this.editQuestion = null;
        this.loadQuestions();
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to update question.';
        console.error('Error updating question:', err);
      }
    });
  }

  deleteQuestion(questionId: number) {
    if (confirm('Are you sure you want to delete this question?')) {
      this.examService.deleteQuestion(this.examId, questionId).subscribe({
        next: () => this.loadQuestions(),
        error: (err) => {
          this.error = err.error?.msg || 'Failed to delete question.';
          console.error('Error deleting question:', err);
        }
      });
    }
  }
}