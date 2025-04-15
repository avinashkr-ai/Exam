import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { map, take } from 'rxjs/operators';

export const AuthGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const expectedRole = route.data['role'];

  return authService.currentUser.pipe(
    take(1),
    map(user => {
      if (!user || !authService.isAuthenticated()) {
        router.navigate(['/auth/login']);
        return false;
      }
      if (expectedRole && user.role !== expectedRole) {
        router.navigate(['/auth/login']);
        return false;
      }
      if (!user.is_verified) {
        router.navigate(['/auth/login'], { queryParams: { error: 'Account not verified' } });
        return false;
      }
      return true;
    })
  );
};