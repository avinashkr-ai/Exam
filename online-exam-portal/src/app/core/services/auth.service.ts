import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { User } from '../models/user';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser = this.currentUserSubject.asObservable();
  private TOKEN_KEY = 'auth_token';

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.loadUserFromStorage();
  }

  private redirectBasedOnRole(role: string | undefined) {
    if (!role) return;
    
    const roleLower = role.toLowerCase();
    switch (roleLower) {
      case 'student':
        this.router.navigate(['/student']);
        break;
      case 'teacher':
        this.router.navigate(['/teacher']);
        break;
      case 'admin':
        this.router.navigate(['/admin']);
        break;
      default:
        this.router.navigate(['/auth/login']);
    }
  }

  login(credentials: { email: string; password: string }): Observable<{ access_token: string }> {
    return this.http.post<{ access_token: string }>(`${this.apiUrl}/auth/login`, credentials).pipe(
      tap(response => {
        if (response.access_token) {
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          this.fetchUser().subscribe({
            next: (user) => {
              if (user) {
                this.currentUserSubject.next(user);
                this.redirectBasedOnRole(user.role);
              } else {
                this.clearAuth();
              }
            },
            error: (err) => {
              console.error('Failed to fetch user:', err);
              this.clearAuth();
            }
          });
        }
      })
    );
  }

  register(user: { name: string; email: string; password: string; role?: string }): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/register`, user);
  }

  logout(): Observable<void> {
    return this.http.post<{ msg: string }>(`${this.apiUrl}/auth/logout`, {}).pipe(
      tap(() => this.clearAuth()),
      map(() => void 0),
      catchError(() => {
        this.clearAuth();
        return of(void 0);
      })
    );
  }

  fetchUser(): Observable<User | null> {
    const token = this.getToken();
    if (!token) {
      console.warn('No token for /auth/me');
      return of(null);
    }
    console.log('Fetching /auth/me with token:', token);
    return this.http.get<User>(`${this.apiUrl}/auth/me`).pipe(
      catchError((err) => {
        console.error('Error fetching /auth/me:', err);
        return of(null);
      })
    );
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }
  
  private clearAuth() {
    localStorage.removeItem(this.TOKEN_KEY);
    this.currentUserSubject.next(null);
  }

  loadUserFromStorage() {
    const token = this.getToken();
    if (token) {
      this.fetchUser().subscribe(user => {
        if (user) {
          this.currentUserSubject.next(user);
          this.redirectBasedOnRole(user.role);
        } else {
          this.clearAuth();
        }
      });
    }
  }

}