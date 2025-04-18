import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { catchError, throwError } from 'rxjs';
import { Router } from '@angular/router';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = authService.getToken();

  if (req.url.includes('/auth/login') || 
      req.url.includes('/auth/register') || 
      req.url.includes('/auth/refresh')) {
    return next(req);
  }
  
  if (token) {
    const cloned = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(cloned).pipe(
      catchError(err => {
        if (err.status === 401) {
          // Only logout if it's not a token refresh attempt
          if (!req.url.includes('/auth/refresh')) {
            authService.logout().subscribe(() => {
              router.navigate(['/auth/login']);
            });
          }
        }
        return throwError(() => err);
      })
    );
  }

  return next(req);
};