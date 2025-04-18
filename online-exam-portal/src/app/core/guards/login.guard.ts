 // src/app/core/guards/login.guard.ts
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { map, take } from 'rxjs/operators';

export const loginGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.currentUser.pipe(
    take(1),
    map(user => {
      if (user && authService.isAuthenticated()) {
        const role = user.role?.toLowerCase();
        switch (role) {
          case 'student':
            router.navigate(['/student']);
            break;
          case 'teacher':
            router.navigate(['/teacher']);
            break;
          case 'admin':
            router.navigate(['/admin']);
            break;
          default:
            router.navigate(['/auth/login']);
        }
        return false;
      }
      return true;
    })
  );
};