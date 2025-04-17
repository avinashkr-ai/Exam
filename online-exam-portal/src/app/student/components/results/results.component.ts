import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { Result } from '../../../core/models/result';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './results.component.html'
})
export class ResultsComponent implements OnInit {
  results: Result[] = [];
  error: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadResults();
  }

  loadResults() {
    this.apiService.getStudentResults().subscribe({
      next: (results) => {
        this.results = results;
        console.log('Results loaded:', results);
      },
      error: (err) => {
        this.error = err.error?.msg || 'Failed to load results.';
        console.error('Error loading results:', err);
      }
    });
  }
}