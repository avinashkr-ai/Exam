import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { User } from '../models/user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl; // 'http://127.0.0.1:5000'
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadUserFromStorage();
  }

  private loadUserFromStorage() {
    const token = this.getToken();
    if (token) {
      this.fetchUser().subscribe({
        next: (user) => {
          console.log('Loaded user from storage:', user);
          if (user) {
            this.currentUserSubject.next(user);
          } else {
            this.clearAuth();
          }
        },
        error: (err) => {
          console.error('Error loading user:', err);
          this.clearAuth();
        }
      });
    }
  }

  login(credentials: { email: string; password: string }): Observable<{ access_token: string }> {
    return this.http.post<{ access_token: string }>(`${this.apiUrl}/auth/login`, credentials).pipe(
      tap(response => {
        console.log('Login response:', response);
        if (response.access_token) {
          localStorage.setItem('token', response.access_token);
          console.log('Token stored:', response.access_token);
          this.fetchUser().subscribe({
            next: (user) => {
              console.log('Fetched user:', user);
              this.currentUserSubject.next(user);
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

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  private clearAuth() {
    console.log('Clearing auth state');
    localStorage.removeItem('token');
    this.currentUserSubject.next(null);
  }
}