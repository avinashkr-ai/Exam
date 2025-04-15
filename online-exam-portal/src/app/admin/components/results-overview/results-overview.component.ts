import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-results-overview',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './results-overview.component.html'
})
export class ResultsOverviewComponent implements OnInit {
  results: any[] = [];
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.loadResults();
  }

  loadResults() {
    this.loading = true;
    this.error = null;
    this.apiService.getAllResults().subscribe({
      next: (data) => {
        this.results = data.results;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load results';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
      }
    });
  }
}