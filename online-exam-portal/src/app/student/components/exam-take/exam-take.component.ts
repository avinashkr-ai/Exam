import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Question } from '../../../core/models/question';

@Component({
  selector: 'app-exam-take',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './exam-take.component.html'
})
export class ExamTakeComponent implements OnInit {
  examId: number;
  exam: { exam_id: number; exam_title: string; questions: Question[]; time_remaining_seconds: number } | null = null;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private route: ActivatedRoute
  ) {
    this.examId = +this.route.snapshot.paramMap.get('id')!;
  }

  ngOnInit() {
    this.loadExam();
  }

  loadExam() {
    this.apiService.takeExam(this.examId).subscribe({
      next: (data) => {
        this.exam = data;
        console.log('Exam loaded:', data);
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to load exam.';
        console.error('Error loading exam:', err);
      }
    });
  }
}