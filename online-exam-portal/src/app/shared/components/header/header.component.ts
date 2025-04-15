import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { User } from '../../../core/models/user';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './header.component.html'
})
export class HeaderComponent {
  currentUser: User | null = null;
  isAuthenticated = false;

  constructor(public authService: AuthService, private router: Router) {
    this.authService.currentUser.subscribe(user => {
      this.currentUser = user;
      this.isAuthenticated = this.authService.isAuthenticated();
    });
  }

  logout() {
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/auth/login']);
      }
    });
  }
}