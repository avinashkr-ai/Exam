import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Exam } from '../../../core/models/exam';

@Component({
  selector: 'app-exam-list',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './exam-list.component.html'
})
export class ExamListComponent implements OnInit {
  exams: Exam[] = [];
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.loadExams();
  }

  loadExams() {
    this.loading = true;
    this.error = null;
    this.apiService.getAvailableExams().subscribe({
      next: (exams) => {
        this.exams = exams;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load exams';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
      }
    });
  }
}