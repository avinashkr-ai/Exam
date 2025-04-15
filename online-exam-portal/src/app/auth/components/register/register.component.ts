import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorAlertComponent } from '../../../shared/components/error-alert/error-alert.component';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent, ErrorAlertComponent],
  templateUrl: './register.component.html'
})
export class RegisterComponent {
  user = { name: '', email: '', password: '', role: 'Student' };
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
    this.authService.register(this.user).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/auth/login']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.msg || 'Registration failed';
        this.errorHandler.handleError(this.error || '');
      }
    });
  }
}