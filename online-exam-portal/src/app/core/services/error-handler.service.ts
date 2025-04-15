import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ErrorHandlerService {
  private errorSubject = new BehaviorSubject<string | null>(null);
  error$ = this.errorSubject.asObservable();

  handleError(message: string | null) {
    this.errorSubject.next(message);
  }

  clearError() {
    this.errorSubject.next(null);
  }
}