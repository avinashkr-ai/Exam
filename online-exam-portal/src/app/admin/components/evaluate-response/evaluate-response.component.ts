import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-evaluate-response',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './evaluate-response.component.html'
})
export class EvaluateResponseComponent implements OnInit {
  response: any = null;
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private route: ActivatedRoute,
    private router: Router,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.response = { response_id: this.route.snapshot.paramMap.get('id') };
  }

  evaluate() {
    this.loading = true;
    this.error = null;
    const responseId = Number(this.route.snapshot.paramMap.get('id'));
    this.apiService.evaluateResponse(responseId).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/admin/results-overview']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to evaluate response';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
      }
    });
  }
}