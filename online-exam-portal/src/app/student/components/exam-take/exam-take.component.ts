import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { interval, Observable, Subject } from 'rxjs';
import { takeUntil, map } from 'rxjs/operators';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-exam-take',
  standalone: true,
  imports: [CommonModule, FormsModule, KeyValuePipe, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './exam-take.component.html'
})
export class ExamTakeComponent implements OnInit, OnDestroy {
  examId: number;
  exam: any = null;
  answers: { question_id: number; response_text: string }[] = [];
  timeRemaining: Observable<number> | null = null;
  loading = false;
  error: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private apiService: ApiService,
    private route: ActivatedRoute,
    private router: Router,
    private errorHandler: ErrorHandlerService
  ) {
    this.examId = Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit() {
    this.loadExam();
  }

  loadExam() {
    this.loading = true;
    this.error = null;
    this.apiService.takeExam(this.examId).subscribe({
      next: (exam) => {
        this.exam = exam;
        this.answers = exam.questions.map((q: any) => ({
          question_id: q.id,
          response_text: ''
        }));
        this.timeRemaining = interval(1000).pipe(
          takeUntil(this.destroy$),
          map(() => {
            exam.time_remaining_seconds--;
            if (exam.time_remaining_seconds <= 0) {
              this.submitExam();
            }
            return exam.time_remaining_seconds;
          })
        );
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load exam';
        this.errorHandler.handleError(this.error || '');
      }
    });
  }

  submitExam() {
    this.loading = true;
    this.error = null;
    this.apiService.submitExam(this.examId, this.answers).subscribe({
      next: () => {
        this.loading = false;
        this.destroy$.next();
        this.router.navigate(['/student/results']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to submit exam';
        this.errorHandler.handleError(this.error || '');
      }
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}