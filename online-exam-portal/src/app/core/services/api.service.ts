import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Exam } from '../models/exam';
import { Result } from '../models/result';
import { Question } from '../models/question';
import { User } from '../models/user';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Admin APIs (unchanged)
  getAdminDashboard(): Observable<any> {
    return this.http.get(`${this.baseUrl}/admin/dashboard`);
  }
  getPendingUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.baseUrl}/admin/users/pending`);
  }
  verifyUser(userId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/users/verify/${userId}`, {});
  }
  deleteUser(userId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/admin/users/${userId}`);
  }
  getAllResults(): Observable<any> {
    return this.http.get(`${this.baseUrl}/admin/results/all`);
  }
  evaluateResponse(responseId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/admin/evaluate/response/${responseId}`, {});
  }

  // Teacher APIs (unchanged)
  getTeacherExams(): Observable<Exam[]> {
    return this.http.get<Exam[]>(`${this.baseUrl}/teacher/exams`);
  }
  createExam(exam: { title: string; description: string; scheduled_time_utc: string; duration_minutes: number }): Observable<any> {
    return this.http.post(`${this.baseUrl}/teacher/exams`, exam);
  }
  getExam(examId: number): Observable<Exam> {
    return this.http.get<Exam>(`${this.baseUrl}/teacher/exams/${examId}`);
  }
  updateExam(examId: number, exam: Partial<Exam>): Observable<any> {
    return this.http.put(`${this.baseUrl}/teacher/exams/${examId}`, exam);
  }
  deleteExam(examId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/teacher/exams/${examId}`);
  }
  addQuestion(examId: number, question: Partial<Question>): Observable<any> {
    return this.http.post(`${this.baseUrl}/teacher/exams/${examId}/questions`, question);
  }
  getQuestions(examId: number): Observable<Question[]> {
    return this.http.get<Question[]>(`${this.baseUrl}/teacher/exams/${examId}/questions`);
  }
  updateQuestion(examId: number, questionId: number, question: Partial<Question>): Observable<any> {
    return this.http.put(`${this.baseUrl}/teacher/exams/${examId}/questions/${questionId}`, question);
  }
  deleteQuestion(examId: number, questionId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/teacher/exams/${examId}/questions/${questionId}`);
  }
  getExamResults(examId: number): Observable<any> {
    return this.http.get(`${this.baseUrl}/teacher/exams/results/${examId}`);
  }

  // Student APIs
  getStudentDashboard(): Observable<{ message: string; completed_exams_count: number; upcoming_exams: Exam[] }> {
    return this.http.get<{ message: string; completed_exams_count: number; upcoming_exams: Exam[] }>(`${this.baseUrl}/student/dashboard`);
  }

  getAvailableExams(): Observable<Exam[]> {
    return this.http.get<Exam[]>(`${this.baseUrl}/student/exams/available`);
  }

  takeExam(examId: number): Observable<{
    exam_id: number;
    exam_title: string;
    scheduled_time_utc: string;
    duration_minutes: number;
    questions: Question[];
    time_remaining_seconds: number;
  }> {
    return this.http.get<{
      exam_id: number;
      exam_title: string;
      scheduled_time_utc: string;
      duration_minutes: number;
      questions: Question[];
      time_remaining_seconds: number;
    }>(`${this.baseUrl}/student/exams/${examId}/take`);
  }

  submitExam(examId: number, answers: { question_id: number; response_text: string }[]): Observable<{ msg: string }> {
    return this.http.post<{ msg: string }>(`${this.baseUrl}/student/exams/${examId}/submit`, { answers });
  }

  getStudentResults(): Observable<Result[]> {
    return this.http.get<Result[]>(`${this.baseUrl}/student/results/my`);
  }
}