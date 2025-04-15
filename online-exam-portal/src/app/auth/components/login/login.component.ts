import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';
import { filter, take } from 'rxjs/operators';
import { User } from '../../../core/models/user';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './login.component.html'
})
export class LoginComponent {
  credentials = { email: 'teacher1@example.com', password: 'password' };
  loading = false;
  error: string | null = null;

  constructor(
    private authService: AuthService,
    private router: Router,
    private errorHandler: ErrorHandlerService
  ) {}

  onSubmit() {
    this.loading = true;
    this.error = null;
    this.authService.login(this.credentials).subscribe({
      next: () => {
        this.authService.currentUser.pipe(
          filter((user): user is User => user !== null && user.role !== undefined),
          take(1)
        ).subscribe({
          next: (user) => {
            this.loading = false;
            if (user.is_verified) {
              const rolePath = user.role.toLowerCase();
              console.log('Redirecting to:', `/${rolePath}`);
              this.router.navigate([`/${rolePath}`], { replaceUrl: true });
            } else {
              this.error = 'Account not verified. Contact an admin.';
              console.error('Login error:', this.error);
              this.errorHandler.handleError(this.error);
              this.authService.logout().subscribe(() => {
                this.router.navigate(['/auth/login']);
              });
            }
          },
          error: () => {
            this.loading = false;
            this.error = 'Unable to fetch user details. Please try again.';
            console.error('CurrentUser error:', this.error);
            this.errorHandler.handleError(this.error);
            this.authService.logout().subscribe(() => {
              this.router.navigate(['/auth/login']);
            });
          }
        });
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Login failed. Check your credentials.';
        console.error('Login API error:', err);
        this.errorHandler.handleError(this.error);
      }
    });
  }
}