export interface Exam {
  id: number;
  title: string;
  description?: string;
  scheduled_time_utc: string;
  duration_minutes?: number;
  created_by?: number;
  created_at_utc?: string;
  status?: 'Upcoming' | 'Active';
}