export interface User {
    id: number;
    name: string;
    email: string;
    role: 'Admin' | 'Teacher' | 'Student';
    is_verified: boolean;
  }