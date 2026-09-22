// API types and interfaces
export interface TimetableItem {
  course?: string;
  course_title?: string;
  faculty?: string;
  room?: string;
  time?: string;
  semester?: string;
  campus?: string;
  [key: string]: any;
}

export interface TimetableData {
  for_day: string;
  for_date: string;
  query: string;
  message_id: string | null;
  items: TimetableItem[];
  semesters: string[];
  summary: {
    total_items: number;
    semester_breakdown: Record<string, number>;
    unique_courses: number;
    unique_faculty: number;
  };
  search?: {
    parser_version?: number;
    query?: string;
    saved_at?: string;
    source_stale?: boolean;
    source_item_count?: number;
    recognized?: boolean;
    answer: string;
    intent: 'schedule' | 'free_time';
    match_mode?: 'intersection' | 'union';
    query_plan?: {
      intent: 'schedule' | 'free_time';
      day_scope: string[];
      combination: 'intersection' | 'union';
      filters: Record<string, string[]>;
    };
    conflict_count?: number;
    conflicts?: Array<{
      day: string;
      overlap: string;
      left: { course?: string; section?: string; time?: string };
      right: { course?: string; section?: string; time?: string };
    }>;
    days: string[];
    entities: Record<string, string[]>;
    free_slots: Record<string, string[]>;
    faculty_availability?: Array<{
      faculty: string;
      slots: Record<string, string[]>;
    }>;
  };
}

export interface BootstrapData {
  success: boolean;
  user: { id: string; email: string };
  config: ConfigData;
  timetable: TimetableData | null;
  last_update: string | null;
  timestamp: string;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp: string;
  cached?: boolean;
}

export interface ConfigData {
  gmail_query: string;
  semester_filter: string[];
  filter_mode?: 'semesters' | 'subjects' | 'faculty';
  subject_filters?: string[];
  faculty_filters?: string[];
  timetable_day?: string;
  personal_email?: string;
  daily_email_enabled?: boolean;
  daily_email_last_result?: {
    status?: 'running' | 'scraping' | 'sending' | 'success' | 'error';
    success?: boolean | null;
    message?: string;
    error?: string;
    personal_email?: string;
    items?: number;
    send_result?: {
      provider?: string;
      message_id?: string;
      thread_id?: string;
      subject?: string;
      from?: string;
      to?: string;
    };
    started_at?: string;
    finished_at?: string;
  } | null;
  schedule_time: string;
  timezone: string;
  max_results: number;
}

export interface StatusData {
  timestamp: string;
  cache_exists: boolean;
  last_update: string | null;
}
