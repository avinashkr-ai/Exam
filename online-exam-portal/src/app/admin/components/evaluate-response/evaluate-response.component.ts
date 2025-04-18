import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface EvaluationResult {
  evaluation_id: number;
  student_name: string;
  student_email: string;
  exam_title: string;
  question_text: string;
  student_response: string;
  marks_awarded: number;
  marks_possible: number;
  feedback: string;
  evaluated_by: string;
  evaluated_at_utc: string;
}

@Component({
  selector: 'app-evaluate-response',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent, ErrorAlertComponent, RouterLink],
  templateUrl: './evaluate-response.component.html'
})
export class EvaluateResponseComponent implements OnInit {
  results: EvaluationResult[] = [];
  loading = false;
  error: string | null = null;
  currentPage = 1;
  totalPages = 1;
  totalResults = 0;
  perPage = 20;
  
  // For individual response evaluation
  selectedResponse: any = null;
  isEvaluating = false;
  manualMarks: number | null = null;
  manualEvaluation: string = '';
  isSubmitting = false;

  constructor(
    private apiService: ApiService,
    private router: Router,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.loadResults();
  }

  loadResults(page: number = 1) {
    this.loading = true;
    this.error = null;
    
    this.apiService.getAllResults(page, this.perPage).subscribe({
      next: (response) => {
        this.results = response.results;
        this.totalPages = response.total_pages;
        this.totalResults = response.total_results;
        this.currentPage = response.current_page;
        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.error = error.error?.msg || 'Failed to load results';
        this.errorHandler.handleError(this.error);
      }
    });
  }

  loadResponse(responseId: number) {
    this.loading = true;
    this.error = null;
    
    this.apiService.getResponseById(responseId).subscribe({
      next: (response) => {
        this.selectedResponse = response;
        this.manualMarks = response.marks || null;
        this.manualEvaluation = response.manual_evaluation || '';
        this.loading = false;
      },
      error: (error) => {
        this.loading = false;
        this.error = error.error?.msg || 'Failed to load response';
        this.errorHandler.handleError(this.error);
      }
    });
  }

  triggerAIEvaluation(responseId: number) {
    this.isEvaluating = true;
    this.error = null;
    
    this.apiService.evaluateResponse(responseId).subscribe({
      next: (response) => {
        // Update the response in the list
        const index = this.results.findIndex(r => r.evaluation_id === responseId);
        if (index !== -1) {
          this.results[index] = {
            ...this.results[index],
            marks_awarded: response.marks_awarded,
            feedback: response.feedback,
            evaluated_by: 'AI System',
            evaluated_at_utc: new Date().toISOString()
          };
        }
        this.isEvaluating = false;
      },
      error: (error) => {
        this.isEvaluating = false;
        this.error = error.error?.msg || 'Failed to evaluate response';
        this.errorHandler.handleError(this.error);
      }
    });
  }

  submitEvaluation() {
    if (!this.selectedResponse || !this.manualMarks) return;
    
    this.isSubmitting = true;
    this.error = null;
    
    const evaluationData = {
      response_id: this.selectedResponse.response_id,
      marks: this.manualMarks,
      evaluation: this.manualEvaluation
    };
    
    this.apiService.submitEvaluation(evaluationData).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.selectedResponse = null;
        this.loadResults(this.currentPage); // Refresh the current page
      },
      error: (error) => {
        this.isSubmitting = false;
        this.error = error.error?.msg || 'Failed to submit evaluation';
        this.errorHandler.handleError(this.error);
      }
    });
  }

  changePage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.loadResults(page);
    }
  }

  closeEvaluation() {
    this.selectedResponse = null;
    this.manualMarks = null;
    this.manualEvaluation = '';
  }
}