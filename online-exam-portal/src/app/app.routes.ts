// src/app/app.routes.ts
import { Routes } from '@angular/router';
import { LoginComponent } from './auth/components/login/login.component';
import { RegisterComponent } from './auth/components/register/register.component';
import { DashboardComponent as AdminDashboard } from './admin/components/dashboard/dashboard.component';
import { UserManagementComponent } from './admin/components/user-management/user-management.component';
import { ResultsOverviewComponent } from './admin/components/results-overview/results-overview.component';
import { EvaluateResponseComponent } from './admin/components/evaluate-response/evaluate-response.component';
import { DashboardComponent as TeacherDashboard } from './teacher/components/dashboard/dashboard.component';
import { ExamManagementComponent } from './teacher/components/exam-management/exam-management.component';
import { QuestionManagementComponent } from './teacher/components/question-management/question-management.component';
import { ExamResultsComponent } from './teacher/components/exam-results/exam-results.component';
import { DashboardComponent as StudentDashboard } from './student/components/dashboard/dashboard.component';
import { ExamListComponent } from './student/components/exam-list/exam-list.component';
import { ExamTakeComponent } from './student/components/exam-take/exam-take.component';
import { ResultsComponent as StudentResults } from './student/components/results/results.component';
import { authGuard } from './core/guards/auth.guard';
import { loginGuard } from './core/guards/login.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/auth/login', pathMatch: 'full' },
  {
    path: 'auth',
    children: [
      { path: 'login', component: LoginComponent },
      { path: 'register', component: RegisterComponent }
    ],
    canActivate: [loginGuard]
  },
  {
    path: 'admin',
    canActivate: [authGuard],
    data: { role: 'admin' },
    children: [
      { path: '', component: AdminDashboard },
      { path: 'user-management', component: UserManagementComponent },
      { path: 'results-overview', component: ResultsOverviewComponent },
      { path: 'evaluate-response', component: EvaluateResponseComponent },
      { path: 'evaluate-response/:id', component: EvaluateResponseComponent }
    ]
  },
  {
    path: 'teacher',
    canActivate: [authGuard],
    data: { role: 'teacher' },
    children: [
      { path: '', component: TeacherDashboard },
      { path: 'exam-management', component: ExamManagementComponent },
      { path: 'question-management/:id', component: QuestionManagementComponent },
      { path: 'exam-results', component: ExamResultsComponent }
    ]
  },
  {
    path: 'student',
    canActivate: [authGuard],
    data: { role: 'student' },
    children: [
      { path: '', component: StudentDashboard },
      { path: 'exam', component: ExamListComponent },
      { path: 'exam/:id/take', component: ExamTakeComponent },
      { path: 'results', component: StudentResults }
    ]
  },
  { path: '**', redirectTo: '/auth/login' }
];