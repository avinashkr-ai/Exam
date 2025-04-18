import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface Response {
  response_id: number;
  exam_id: number;
  exam_title: string;
  question_id: number;
  question_text: string;
  question_type: string;
  marks_possible: number;
  student_name: string;
  student_email: string;
  response_text: string;
  submitted_at_utc: string;
  evaluation_status: string;
  evaluation_id: number | null;
  evaluated_by: string | null;
  evaluated_at_utc: string | null;
  marks_awarded: number | null;
  feedback: string | null;
}

interface ResponseData {
  current_page: number;
  per_page: number;
  responses: Response[];
  total_pages: number;
  total_responses: number;
}

@Component({
  selector: 'app-evaluate-response',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent, ErrorAlertComponent, RouterLink],
  templateUrl: './evaluate-response.component.html'
})
export class EvaluateResponseComponent implements OnInit {
  responses: Response[] = [];
  loading = false;
  error: string | null = null;
  currentPage = 1;
  totalPages = 1;
  totalResponses = 0;
  itemsPerPage = 20;
  
  // For individual response evaluation
  selectedResponse: any = null;
  isEvaluating = false;
  manualMarks: number | null = null;
  manualEvaluation: string = '';
  isSubmitting = false;
  totalResults = 0;

  constructor(
    private apiService: ApiService,
    private router: Router,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.loadResponses();
  }

  loadResponses() {
    this.loading = true;
    this.error = null;
    this.apiService.getAllResponses().subscribe({
      next: (data: ResponseData) => {
        this.responses = data.responses;
        this.currentPage = data.current_page;
        this.totalPages = data.total_pages;
        this.totalResponses = data.total_responses;
        this.itemsPerPage = data.per_page;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load responses';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
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
    if (confirm('Are you sure you want to trigger AI evaluation for this response?')) {
      this.loading = true;
      this.error = null;
      this.apiService.triggerAIEvaluation(responseId).subscribe({
        next: (result) => {
          this.loadResponses();
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.msg || 'Failed to trigger AI evaluation';
          if (this.error) {
            this.errorHandler.handleError(this.error);
          }
        }
      });
    }
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
        this.loadResponses(); // Refresh the current page
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
      this.loadResponses();
    }
  }

  closeEvaluation() {
    this.selectedResponse = null;
    this.manualMarks = null;
    this.manualEvaluation = '';
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'Pending Evaluation':
        return 'bg-warning';
      case 'Evaluated':
        return 'bg-success';
      default:
        return 'bg-secondary';
    }
  }

  getQuestionTypeClass(type: string): string {
    switch (type) {
      case 'MCQ':
        return 'bg-primary';
      case 'SHORT_ANSWER':
        return 'bg-info';
      case 'LONG_ANSWER':
        return 'bg-success';
      default:
        return 'bg-secondary';
    }
  }

  formatDate(dateString: string | null): string {
    if (!dateString) return 'Not evaluated';
    const date = new Date(dateString);
    return date.toLocaleString();
  }
}