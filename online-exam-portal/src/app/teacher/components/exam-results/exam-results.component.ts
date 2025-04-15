import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-exam-results',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './exam-results.component.html'
})
export class ExamResultsComponent implements OnInit {
  examId: number;
  results: any[] = [];
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private route: ActivatedRoute,
    private errorHandler: ErrorHandlerService
  ) {
    this.examId = Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit() {
    this.loadResults();
  }

  loadResults() {
    this.loading = true;
    this.error = null;
    this.apiService.getExamResults(this.examId).subscribe({
      next: (results) => {
        this.results = results;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load results';
        this.errorHandler.handleError(this.error || '');
      }
    });
  }
}