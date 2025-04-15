import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { User } from '../../../core/models/user';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './user-management.component.html'
})
export class UserManagementComponent implements OnInit {
  users: User[] = [];
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private errorHandler: ErrorHandlerService
  ) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading = true;
    this.error = null;
    this.apiService.getPendingUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to load users';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
      }
    });
  }

  verifyUser(userId: number) {
    this.loading = true;
    this.error = null;
    this.apiService.verifyUser(userId).subscribe({
      next: () => {
        this.loadUsers();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Failed to verify user';
        if (this.error) {
          this.errorHandler.handleError(this.error);
        }
      }
    });
  }

  deleteUser(userId: number) {
    if (confirm('Are you sure you want to delete this user?')) {
      this.loading = true;
      this.error = null;
      this.apiService.deleteUser(userId).subscribe({
        next: () => {
          this.loadUsers();
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.msg || 'Failed to delete user';
          if (this.error) {
            this.errorHandler.handleError(this.error);
          }
        }
      });
    }
  }
}