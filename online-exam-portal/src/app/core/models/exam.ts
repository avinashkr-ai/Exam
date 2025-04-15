export interface Exam {
  id: number;
  title: string;
  description: string;
  scheduled_time: string;
  duration: number;
  created_by: number;
  created_at: string;
  status?: 'Active' | 'Inactive' | 'Completed'; // Added status
}