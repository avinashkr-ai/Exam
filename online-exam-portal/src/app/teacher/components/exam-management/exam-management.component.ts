import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Exam } from '../../../core/models/exam';
import { ApiService } from '../../../core/services/api.service';

@Component({
  selector: 'app-exam-management',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './exam-management.component.html'
})
export class ExamManagementComponent implements OnInit {
  exams: Exam[] = [];
  newExam = { title: '', description: '', scheduled_time: '', duration: 0 };
  error: string | null = null;

  constructor(private examService: ApiService) {}

  ngOnInit() {
    this.loadExams();
  }

  loadExams() {
    this.examService.getTeacherExams().subscribe({
      next: (exams) => {
        this.exams = exams;
        console.log('Exams loaded:', exams);
      },
      error: (err) => {
        this.error = 'Failed to load exams.';
        console.error('Error loading exams:', err);
      }
    });
  }

  createExam() {
    if (!this.newExam.title || !this.newExam.scheduled_time || this.newExam.duration <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    this.examService.createExam(this.newExam).subscribe({
      next: () => {
        this.newExam = { title: '', description: '', scheduled_time: '', duration: 0 };
        this.loadExams();
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to create exam.';
        console.error('Error creating exam:', err);
      }
    });
  }
}