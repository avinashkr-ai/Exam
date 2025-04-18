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
  newExam = { title: '', description: '', scheduled_time_utc: '', duration_minutes: 0 };
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
    if (!this.newExam.title || !this.newExam.scheduled_time_utc || this.newExam.duration_minutes <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    this.apiService.createExam(this.newExam).subscribe({
      next: () => {
        this.newExam = { title: '', description: '', scheduled_time_utc: '', duration_minutes: 0 };
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
    if (this.editExam.scheduled_time_utc) {
      this.editExam.scheduled_time_utc = new Date(this.editExam.scheduled_time_utc).toISOString().slice(0, 16);
    }
  }

  updateExam() {
    if (!this.editExam) {
      this.error = 'No exam selected for editing.';
      return;
    }
    const { title, scheduled_time_utc, duration_minutes } = this.editExam;
    if (!title || !scheduled_time_utc || duration_minutes == null || duration_minutes <= 0) {
      this.error = 'Please fill all required fields.';
      return;
    }
    this.apiService.updateExam(this.editExam.id, {
      //  add 5 hours 30 minutes to the scheduled time
      scheduled_time_utc: new Date(new Date(scheduled_time_utc).getTime() + 5 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
      title,
      description: this.editExam.description,
      duration_minutes
    }).subscribe({
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

  deleteExam(examId: number, examTitle: string) {
    if (confirm(`Are you sure you want to delete the exam "${examTitle}"?`)) {
      this.apiService.deleteExam(examId).subscribe({
        next: () => {
          this.error = null;
          this.loadExams();
        },
        error: (err) => {
          this.error = err.error?.msg || 'Failed to delete exam.';
          console.error('Error deleting exam:', err);
        }
      });
    }
  }

  examStatus(exam: Exam): string {
    const now = new Date();
    const examTime = new Date(exam.scheduled_time_utc);
    const examEndTime = new Date(examTime.getTime() + (exam.duration_minutes || 0) * 60000);
    if (now < examTime) {
      return 'Upcoming';
    } else if (now >= examTime && now <= examEndTime) {
      return 'Active';
    } else {
      return 'Expired';
    }
  }

  cancelEdit() {
    this.editExam = null;
    this.error = null;
  }
}