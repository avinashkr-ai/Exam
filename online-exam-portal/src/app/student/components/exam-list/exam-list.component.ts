import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Exam } from '../../../core/models/exam';

@Component({
  selector: 'app-exam-list',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './exam-list.component.html'
})
export class ExamListComponent implements OnInit {
  exams: Exam[] = [];
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadExams();
  }

  loadExams() {
    this.apiService.getAvailableExams().subscribe({
      next: (exams) => {
        this.exams = exams;
        console.log('Available exams loaded:', exams);
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to load exams.';
        console.error('Error loading exams:', err);
      }
    });
  }
}