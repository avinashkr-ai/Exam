import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { Exam } from '../../../core/models/exam';
import { Question } from '../../../core/models/question';

@Component({
  selector: 'app-exam-take',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './exam-take.component.html'
})
export class ExamTakeComponent implements OnInit, OnDestroy {
  exam: any = null;
  currentQuestionIndex: number = 0;
  answers: { [key: number]: string } = {};
  error: string | null = null;
  loading: boolean = true;
  submitting: boolean = false;
  timeLeft: number = 0;
  private timerInterval: any;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    const examId = this.route.snapshot.paramMap.get('id');
    if (examId) {
      this.loadExam(parseInt(examId));
    }
  }

  ngOnDestroy() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  loadExam(examId: number) {
    this.loading = true;
    this.error = null;
    this.apiService.takeExam(examId).subscribe({
      next: (response: any) => {
        if (response.error) {
          this.error = response.error;
          this.loading = false;
          return;
        }
        this.exam = response;
        this.timeLeft = response.time_remaining_seconds || response.duration_minutes * 60;
        this.startTimer();
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to load exam.';
        this.loading = false;
      }
    });
  }

  startTimer() {
    this.timerInterval = setInterval(() => {
      if (this.timeLeft > 0) {
        this.timeLeft--;
      } else {
        this.submitExam();
      }
    }, 1000);
  }

  get currentQuestion(): Question | null {
    return this.exam?.questions[this.currentQuestionIndex] || null;
  }

  onAnswerChange(event: any) {
    if (this.currentQuestion) {
      const value = event.target ? event.target.value : event;
      this.answers[this.currentQuestion.id] = value;
    }
  }

  getWordCount(text: string | undefined): number {
    if (!text) return 0;
    return text.split(/\s+/).filter(word => word.length > 0).length;
  }

  previousQuestion() {
    if (this.currentQuestionIndex > 0) {
      this.currentQuestionIndex--;
    }
  }

  nextQuestion() {
    if (this.exam && this.currentQuestionIndex < this.exam.questions.length - 1) {
      this.currentQuestionIndex++;
    }
  }

  saveProgress() {
    if (!this.exam) return;
    
    // Convert answers to the format expected by the API
    const formattedAnswers = Object.entries(this.answers).map(([id, text]) => ({
      question_id: parseInt(id),
      response_text: text
    }));
    
    this.apiService.submitExam(this.exam.exam_id, formattedAnswers).subscribe({
      next: () => {
        // Show success message or handle as needed
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to save progress.';
      }
    });
  }

  confirmSubmit() {
    if (confirm('Are you sure you want to submit the exam? This action cannot be undone.')) {
      this.submitExam();
    }
  }

  submitExam() {
    if (!this.exam) return;
    
    this.submitting = true;
    
    // Convert answers to the format expected by the API
    const formattedAnswers = Object.entries(this.answers).map(([id, text]) => ({
      question_id: parseInt(id),
      response_text: text
    }));
    
    this.apiService.submitExam(this.exam.exam_id, formattedAnswers).subscribe({
      next: (response) => {
        this.submitting = false;
        this.router.navigate(['/student/results'], { 
          queryParams: { examId: this.exam?.exam_id }
        });
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to submit exam.';
        this.submitting = false;
      }
    });
  }

  get formattedTimeLeft(): string {
    const hours = Math.floor(this.timeLeft / 3600);
    const minutes = Math.floor((this.timeLeft % 3600) / 60);
    const seconds = this.timeLeft % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }

  get progress(): number {
    if (!this.exam) return 0;
    return ((this.currentQuestionIndex + 1) / this.exam.questions.length) * 100;
  }
}