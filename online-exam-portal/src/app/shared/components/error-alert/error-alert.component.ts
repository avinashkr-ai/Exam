import { Component, Input } from '@angular/core';
import { ErrorHandlerService } from '../../../core/services/error-handler.service';

@Component({
  selector: 'app-error-alert',
  standalone: true,
  templateUrl: './error-alert.component.html'
})
export class ErrorAlertComponent {
  @Input() message: string | null = null;

  constructor(private errorHandler: ErrorHandlerService) {}

  clearError() {
    this.errorHandler.clearError();
  }
}