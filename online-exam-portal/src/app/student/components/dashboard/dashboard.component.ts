import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Exam } from '../../../core/models/exam';

@Component({
  selector: 'DashboardComponent',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html'
})

export class DashboardComponent implements OnInit {
  completedExamsCount: number = 0;
  upcomingExams: Exam[] = [];
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadDashboard();
  }

  loadDashboard() {
    this.apiService.getStudentDashboard().subscribe({
      next: (data) => {
        this.completedExamsCount = data.completed_exams_count;
        this.upcomingExams = data.upcoming_exams;
        console.log('Dashboard loaded:', data);
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to load dashboard.';
        console.error('Error loading dashboard:', err);
      }
    });
  }
}