import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { Exam } from '../../../core/models/exam';

interface DashboardData {
  message: string;
  completed_exams_count: number;
  upcoming_exams: Exam[];
}

interface ExamStatus {
  status: 'Upcoming' | 'Active' | 'Expired';
  class: string;
}

@Component({
  selector: 'app-student-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  completedExamsCount = 0;
  upcomingExams: Exam[] = [];
  loading = false;
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadDashboardData();
  }

  loadDashboardData() {
    this.loading = true;
    this.error = null;

    this.apiService.getStudentDashboard().subscribe({
      next: (data: { message: string; completed_exams_count: number; upcoming_exams: Exam[] }) => {
        this.completedExamsCount = data.completed_exams_count;
        this.upcomingExams = data.upcoming_exams;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load dashboard data';
        console.error('Error fetching dashboard data:', err);
      }
    });
  }

  getExamStatus(exam: Exam): ExamStatus {
    const now = new Date();
    const examTime = new Date(exam.scheduled_time_utc);
    const examEndTime = new Date(examTime.getTime() + (exam.duration_minutes || 0) * 60000);

    if (now < examTime) {
      return {
        status: 'Upcoming',
        class: 'badge bg-warning'
      };
    } else if (now >= examTime && now <= examEndTime) {
      return {
        status: 'Active',
        class: 'badge bg-success'
      };
    } else {
      return {
        status: 'Expired',
        class: 'badge bg-danger'
      };
    }
  }

  canStartExam(exam: Exam): boolean {
    const status = this.getExamStatus(exam);
    return status.status === 'Active';
  }

  formatDateTime(dateTimeStr: string): string {
    return new Date(dateTimeStr).toLocaleString();
  }
}