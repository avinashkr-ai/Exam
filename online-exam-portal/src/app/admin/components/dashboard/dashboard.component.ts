import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

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
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  stats: AdminStats | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<AdminStats>(`${environment.apiUrl}/admin/dashboard`).subscribe({
      next: (data) => {
        this.stats = data;
        console.log('Admin stats:', data);
      },
      error: (err) => console.error('Error fetching admin stats:', err)
    });
  }
}