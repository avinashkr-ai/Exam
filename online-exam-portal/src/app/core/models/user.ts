export interface User {
    id: number;
    name: string;
    email: string;
    role: 'ADMIN' | 'TEACHER' | 'STUDENT';
    is_verified: boolean;
  }