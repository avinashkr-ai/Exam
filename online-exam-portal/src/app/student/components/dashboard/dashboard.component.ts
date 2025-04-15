import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Exam } from '../../../core/models/exam';

interface StudentStats {
  completed_exams_count: number;
  upcoming_exams: Exam[];
}

@Component({
  selector: 'app-student-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  stats: StudentStats | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.http.get<StudentStats>(`${environment.apiUrl}/student/dashboard`).subscribe({
      next: (data) => {
        this.stats = data;
        console.log('Student stats:', data);
      },
      error: (err) => console.error('Error fetching student stats:', err)
    });
  }
}