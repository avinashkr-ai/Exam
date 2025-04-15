import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../core/services/api.service';
import { Exam } from '../../../core/models/exam';

@Component({
  selector: 'app-exam-management',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './exam-management.component.html'
})
export class ExamManagementComponent implements OnInit {
  exams: Exam[] = [];
  newExam = { title: '', description: '', scheduled_time: '', duration: 0 };
  editExam: Exam | null = null;
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadExams();
  }

  loadExams() {
    this.apiService.getTeacherExams().subscribe({
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
    this.apiService.createExam(this.newExam).subscribe({
      next: () => {
        this.newExam = { title: '', description: '', scheduled_time: '', duration: 0 };
        this.error = null;
        this.loadExams();
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to create exam.';
        console.error('Error creating exam:', err);
      }
    });
  }

  startEdit(exam: Exam) {
    this.editExam = { ...exam };
    // Convert scheduled_time to datetime-local format (YYYY-MM-DDTHH:MM)
    if (this.editExam.scheduled_time) {
      this.editExam.scheduled_time = new Date(this.editExam.scheduled_time).toISOString().slice(0, 16);
    }
  }

  updateExam() {
    if (!this.editExam || !this.editExam.title || !this.editExam.scheduled_time || this.editExam.duration <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    this.apiService.updateExam(this.editExam.id, this.editExam).subscribe({
      next: () => {
        this.editExam = null;
        this.error = null;
        this.loadExams();
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to update exam.';
        console.error('Error updating exam:', err);
      }
    });
  }

  cancelEdit() {
    this.editExam = null;
    this.error = null;
  }
}