import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface TeacherStats {
  my_exams_count: number;
}

@Component({
  selector: 'app-teacher-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  stats: TeacherStats | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<TeacherStats>(`${environment.apiUrl}/teacher/dashboard`).subscribe({
      next: (data) => {
        this.stats = data;
        console.log('Teacher stats:', data);
      },
      error: (err) => console.error('Error fetching teacher stats:', err)
    });
  }
}