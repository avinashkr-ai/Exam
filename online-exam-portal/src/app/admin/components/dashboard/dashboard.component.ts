import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';

interface AdminStats {
  active_teachers: number;
  active_students: number;
  pending_verifications: number;
  total_exams: number;
  total_responses_submitted: number;
  responses_evaluated: number;
  responses_pending_evaluation: number;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  stats: AdminStats | null = null;
  loading = false;
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadDashboardStats();
  }

  loadDashboardStats() {
    this.loading = true;
    this.error = null;

    this.apiService.getAdminDashboard().subscribe({
      next: (data) => {
        this.stats = data;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load dashboard statistics';
        console.error('Error fetching admin stats:', err);
      }
    });
  }

  // Helper method to calculate evaluation progress percentage
  getEvaluationProgress(): number {
    if (!this.stats) return 0;
    const total = this.stats.total_responses_submitted;
    if (total === 0) return 100;
    return Math.round((this.stats.responses_evaluated / total) * 100);
  }

  // Helper method to get verification progress percentage
  getVerificationProgress(): number {
    if (!this.stats) return 0;
    const total = this.stats.active_teachers + this.stats.active_students + this.stats.pending_verifications;
    if (total === 0) return 100;
    return Math.round(((this.stats.active_teachers + this.stats.active_students) / total) * 100);
  }
}