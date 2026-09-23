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
      selection_scope?: {
        base_sections: string[];
        course_section_pairs: Array<{
          section: string;
          kind: 'course' | 'code';
          value: string;
          class_types: Array<'theory' | 'lab' | 'fyp'>;
        }>;
        unpaired_courses: string[];
        unpaired_codes: string[];
        global_class_types: Array<'theory' | 'lab' | 'fyp'>;
      } | null;
    };
    conflict_count?: number;
    conflicts?: TimetableConflict[];
    days: string[];
    entities: Record<string, string[]>;
    free_slots: Record<string, string[]>;
    faculty_availability?: Array<{
      faculty: string;
      slots: Record<string, string[]>;
    }>;
  };
}

export interface TimetableConflictClass {
  course?: string;
  section?: string;
  time?: string;
}

export interface TimetableConflict {
  day: string;
  overlap: string;
  left: TimetableConflictClass;
  right: TimetableConflictClass;
}

export interface BootstrapData {
  success: boolean;
  user: { id: string; email: string };
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
