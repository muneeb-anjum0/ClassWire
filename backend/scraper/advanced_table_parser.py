#!/usr/bin/env python3
"""
Advanced Pandas-based Table Parser for Timetable Data
This replaces the fragile line-by-line parsing with proper table extraction
"""
import pandas as pd
import re
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import io
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class AdvancedTableParser:
    def __init__(self):
        # Define expected column patterns (flexible matching)
        self.column_patterns = {
            'sr_no': r'(?:sr\.?\s*no|serial|s\.?\s*no|#)',
            'dept': r'(?:dept|department)',
            'program': r'(?:program)',
            'semester': r'(?:class|section|semester)',
            'course_code': r'(?:course_code|course|subject|code)',
            'course_title': r'(?:course_title|title|name)',
            'faculty': r'(?:faculty|teacher|instructor)',
            'room': r'(?:room|venue|location)',
            'time': r'(?:time|timing|schedule)',
            'campus': r'(?:campus)',
            'credits': r'(?:credits?|cr\.?)'
        }
        
        # Semester patterns for filtering
        self.semester_patterns = [
            r'BS\s*\([A-Z]{2,4}\)\s*-\s*\d+[A-Z]',
            r'MS\s*\([A-Z]{2,4}\)\s*-\s*\d+[A-Z]',
            r'PhD\s*\([A-Z]{2,4}\)\s*-\s*\d+[A-Z]'
        ]
        
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def find_best_column_match(self, header: str) -> Optional[str]:
        """Find the best matching column type for a header"""
        header_clean = re.sub(r'[^\w\s]', '', header.lower().strip())
        
        best_match = None
        best_score = 0.0
        
        for col_type, pattern in self.column_patterns.items():
            if re.search(pattern, header_clean, re.IGNORECASE):
                # Exact match gets higher priority
                if header_clean == col_type or header_clean.replace('_', '') == col_type.replace('_', ''):
                    return col_type
                    
                match_obj = re.search(pattern, header_clean, re.IGNORECASE)
                score = len(match_obj.group(0)) / len(header_clean) if match_obj else 0
                if score > best_score:
                    best_score = score
                    best_match = col_type
        
        return best_match if best_score > 0.3 else None
    
    def extract_tables_from_html(self, html_content: str) -> List[pd.DataFrame]:
        """Extract all tables from HTML using pandas"""
        tables = []
        
        try:
            # Try pandas read_html first (most robust for actual tables)
            pandas_tables = pd.read_html(html_content, header=0)
            logger.info(f"✅ Pandas found {len(pandas_tables)} HTML tables directly")
            tables.extend(pandas_tables)
        except Exception as e:
            logger.warning(f"⚠️ Pandas read_html failed: {e}")
            
        # Gmail emails often don't have proper tables - extract from text content
        try:
            text_tables = self._extract_tables_from_text(html_content)
            if text_tables:
                logger.info(f"✅ Extracted {len(text_tables)} tables from text content")
                tables.extend(text_tables)
        except Exception as e:
            logger.warning(f"⚠️ Text table extraction failed: {e}")
            
        # Fallback: Use BeautifulSoup to clean and extract any remaining tables
        if not tables:
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                table_elements = soup.find_all('table')
                
                if table_elements:
                    for i, table in enumerate(table_elements):
                        try:
                            table_html = str(table)
                            df_list = pd.read_html(table_html, header=0)
                            tables.extend(df_list)
                            logger.info(f"✅ Extracted HTML table {i+1} with shape {df_list[0].shape}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse HTML table {i+1}: {e}")
                else:
                    logger.warning("❌ No table elements found in HTML")
            except Exception as e:
                logger.error(f"❌ BeautifulSoup fallback failed: {e}")
                
        return tables
    
    def _extract_tables_from_text(self, html_content: str) -> List[pd.DataFrame]:
        """Extract table data from text content (Gmail-style formatting) - ENHANCED FOR ALL 39 SECTIONS"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get all text content, preserving line breaks
        text_content = soup.get_text('\n')
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        logger.info(f"🔍 Processing {len(lines)} lines from Gmail text content")
        
        # Enhanced multi-line reconstruction - FIXED for ALL section patterns
        schedule_entries = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for lines starting with a number (schedule entries)
            # Enhanced pattern to catch ALL section formats including BS, EMBA, PMBA, etc.
            if re.match(r'^\d+\s+[A-Z]{2,4}\s+', line):
                # This is a schedule line that might span multiple lines
                full_entry = line
                
                # Look ahead for continuation lines more aggressively
                j = i + 1
                while j < len(lines) and j < i + 12:  # Look ahead up to 12 lines for complex entries
                    next_line = lines[j].strip()
                    
                    # Stop if we hit another numbered entry (new schedule item)
                    if re.match(r'^\d+\s+[A-Z]{2,4}\s+', next_line):
                        break
                    
                    # Stop if we hit emoji headers/separators
                    if re.match(r'^[🕗🔸]', next_line):
                        break
                    
                    # Include date/time information lines
                    if re.match(r'^\d{1,2}-\d{1,2}-\d{4}', next_line):
                        full_entry += " " + next_line
                        j += 1
                        break
                    
                    # Add continuation lines that contain relevant data
                    if next_line:
                        # Include lines with faculty names, times, rooms, etc.
                        # Enhanced patterns for better continuation detection
                        if (re.search(r'Dr\.|Prof\.|Mr\.|Ms\.|\d{1,2}:\d{2}\s*[AP]M|Hall|Lab|NB-|\d{3}|SZABIST|Campus|Cancelled|Accounting|Management|Ethics|Governance|Marketing|Analysis|Development|Research|International|Engineering|Programming|Computing|Vision|Technical|Business|Communication|Project|Risk|Organizational|Strategic|Supply|Chain|Operations|Fundamentals|Applied|Principles|Assessment|Diagnosis|Quantitative|Qualitative|Psychotherapy|Counseling|Media|Journalism|Participation|Community|Resilience|Vulnerability|Hands-on', next_line, re.IGNORECASE) or
                            len(next_line.split()) <= 8):  # Medium lines are likely continuations
                            full_entry += " " + next_line
                    j += 1
                
                # Only include entries that have valid semester and course patterns
                # Enhanced validation for ALL 39 section types
                has_valid_semester = any([
                    re.search(r'(BS|MS|PhD|EMBA|PMBA|MBA|BBA|MHRM|MPM|MMS)', full_entry),
                    re.search(r'(BSAI|BSSE)', full_entry),  # AI and SE programs
                    re.search(r'Core|Elective|Open|Zero', full_entry),  # Special qualifiers
                ])
                
                has_valid_course = re.search(r'\b[A-Z]{2,4}L?\s*(?:TE)?-?\s*\d{2,4}\b', full_entry)
                
                if has_valid_semester and has_valid_course:
                    schedule_entries.append(full_entry)
                    logger.debug(f"📝 Reconstructed entry {len(schedule_entries)}: {full_entry[:100]}...")
                
                i = j  # Skip the lines we've already processed
            else:
                i += 1
        
        logger.info(f"📝 Found {len(schedule_entries)} potential schedule entries")
        
        if not schedule_entries:
            logger.warning("❌ No valid schedule entries found in text content")
            return []
            
        # Parse entries into structured data
        rows = []
        for i, entry in enumerate(schedule_entries):
            row_data = self._parse_schedule_line(entry)
            if row_data:
                rows.append(row_data)
                if i < 5:  # Log first few for debugging
                    logger.info(f"✅ Parsed entry {i+1}: {row_data.get('course')} - {row_data.get('semester')} - Faculty: {row_data.get('faculty')} - Time: {row_data.get('time')}")
        
        if not rows:
            logger.warning("❌ No valid rows parsed from schedule entries")
            return []
            
        # Create DataFrame with proper column mapping
        df = pd.DataFrame(rows)
        
        logger.info(f"✅ Created DataFrame from text with shape {df.shape}")
        logger.info(f"✅ Columns: {list(df.columns)}")
        
        return [df]
    
    def _parse_schedule_line(self, line: str) -> Optional[Dict]:
        """Parse a single schedule line into structured data - ENHANCED FOR ALL 39 SECTIONS"""
        try:
            logger.debug(f"🔧 Parsing entry: {line[:100]}...")
            
            # Check if this is a cancelled class first
            is_cancelled = 'Cancelled' in line or 'cancelled' in line.lower()
            
            # Extract serial number (at the beginning)
            sr_match = re.match(r'^(\d+)\s+', line)
            sr_no = sr_match.group(1) if sr_match else None
            
            # Extract department (after serial number, before program)
            dept_match = re.search(r'^\d+\s+([A-Z/\s]+?)\s+(?:BS|MS|PhD|EMBA|PMBA|MBA|BBA|MHRM|MPM|MMS)', line)
            dept = dept_match.group(1).strip() if dept_match else None
            
            # Extract semester - Enhanced to handle ALL section formats
            semester_patterns = [
                # Complex multi-section patterns like "EMBA - 1 / PMBA - 1 / MBA (72) Day / Eve - 1"
                r'((?:EMBA|PMBA|MBA)\s*-\s*\d+(?:\s*/\s*(?:EMBA|PMBA|MBA)(?:\s*\(\d+\))?\s*(?:Day|Eve)?\s*-\s*\d+)*)',
                # MS patterns with complex aliases like "MS (SS) - 1 / MSS - 1"
                r'(MS\s*\([A-Z]{2,4}\)\s*-\s*[0-9A-Z]+(?:\s*/\s*[A-Z]{2,4}\s*-\s*[0-9A-Z]+)*)',
                # BS patterns with section letters - FIXED to handle "BS (CS) - 2 C" format
                r'(BS\s*\([A-Z]{2,4}\)\s*-\s*\d+\s*[A-Z]*)',  # "BS (CS) - 2 C", "BS (SE) - 4A"
                r'(BSAI\s*-\s*\d+\s*[A-Z]*)',               # "BSAI - 1B", "BSAI - 4A"  
                r'(BS\s*\(?[A-Z]{2,4}\)?\s*(?:/\s*[A-Z]{2,4})?\s*(?:Open))', # "BS (CS) / BSSE Open"
                # Simple patterns like "BBA - 2", "MMS Zero", "MMS - 1"  
                r'((?:BBA|MMS|MHRM|MPM)\s*(?:-\s*\d+|Zero))',
                # PM patterns with additional qualifiers like "MS (PM) - 1 A Core", "MS (PM) - 2 A & 3 A Elective"
                r'(MS\s*\([A-Z]{2}\)\s*-\s*[0-9A-Z]+\s*[A-Z]*(?:\s*(?:Core|Elective|&\s*\d+\s*[A-Z]*\s*Elective))?)',
                # Generic fallback for any pattern
                r'([A-Z]{2,4}\s*(?:\([A-Z]{2,4}\))?\s*-\s*[0-9A-Z]+(?:\s*[A-Z]+)?)',
            ]
            
            semester = None
            for pattern in semester_patterns:
                semester_match = re.search(pattern, line)
                if semester_match:
                    semester = semester_match.group(1).strip()
                    logger.debug(f"✅ Found semester: {semester}")
                    break
            
            # Extract course code - Enhanced for ALL course code formats INCLUDING DASHES
            course_patterns = [
                r'\b([A-Z]{2,4}L?\s*TE\d{2})\b',          # Special codes like "HR TE11", "PM TE03"
                r'\b([A-Z]{2,4}L?\s*-?\s*\d{2,4})\b',     # Standard codes with optional dash: "BE-5105", "CSC 3202", "BE 5101"
                r'\b([A-Z]{2,3}\s*-?\s*\d{2,4})\b',       # Short codes with optional dash: "MD-2323", "MD 2323"
            ]
            
            course = None
            for pattern in course_patterns:
                course_match = re.search(pattern, line)
                if course_match:
                    course = course_match.group(1).strip()
                    break
            
            # Extract course title - FIXED to handle "/" properly and NOT pick and choose
            course_title = None
            if course_match:
                after_course = line[course_match.end():].strip()
                
                # For titles with "/", capture the ENTIRE title, don't split
                # Pattern: Look for everything until faculty name or time
                title_patterns = [
                    # Pattern 1: Title with credits in parentheses before faculty
                    r'^([^()]+(?:\([0-9,]+\))?)\s+(?:Dr\.|Prof\.|Mr\.|Ms\.|[A-Z][a-z]+\s+[A-Z][a-z]+)',
                    # Pattern 2: Title until faculty name (multiple words starting with capital)
                    r'^([^()]+?)\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:\d{3}|Hall|Lab|\d{1,2}:\d{2})',
                    # Pattern 3: Title until room/time
                    r'^([^()]+?)\s+(?:\d{3}|Hall|Lab|\d{1,2}:\d{2})',
                    # Pattern 4: Title with multiple "/" segments - capture ALL
                    r'^([^()]+(?:/[^()]+)*?)(?:\s*\([0-9,]+\))?\s+(?:Dr\.|Prof\.|[A-Z][a-z]+)',
                    # Pattern 5: Everything until first proper name or room
                    r'^([^()]+?)(?:\s+(?:[A-Z][a-z]+\s+[A-Z][a-z]+|Dr\.|Prof\.)|\s+\d{3}|\s+Hall|\s+Lab)',
                ]
                
                for pattern in title_patterns:
                    title_match = re.search(pattern, after_course)
                    if title_match:
                        course_title = title_match.group(1).strip()
                        break
                
                # Clean up course title - remove trailing punctuation but keep "/"
                if course_title:
                    course_title = re.sub(r'\s*\([0-9,]+\)\s*$', '', course_title).strip()
                    course_title = re.sub(r'[-/\s]+$', '', course_title).strip()
                    # If title is too short and has "/", it might be incomplete - try to get more
                    if '/' in course_title and len(course_title.split('/')[0].strip()) < 3:
                        # Try to get a longer title
                        extended_match = re.search(r'^([^()]+(?:/[^()]+)*)', after_course)
                        if extended_match:
                            extended_title = extended_match.group(1).strip()
                            if len(extended_title) > len(course_title):
                                course_title = extended_title
            
            # Extract faculty name - Enhanced for ALL name formats
            faculty = None
            if not is_cancelled:
                faculty_patterns = [
                    # Pattern 1: "Dr. Faculty Name" (with title)
                    r'\b(Dr\.\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z-]+)*)\s+(?:-\s+)?(?:\d{3}|Hall|Lab|\d{1,2}:\d{2}|Cancelled)',
                    # Pattern 2: Faculty name before room/time (no title) - at least 2 words, handle mixed case
                    r'\b([A-Z][a-z]+\s+[A-Za-z][a-z]*(?:\s+[A-Z][a-z]+)*)\s+(?:-\s+)?(?:\d{3}|Hall|Lab|\d{1,2}:\d{2})',
                    # Pattern 3: Faculty name before "Cancelled"
                    r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)*)\s+Cancelled',
                    # Pattern 4: After credits pattern
                    r'\([0-9,]+\)\s+([A-Z][A-Za-z\s]+?)\s+(?:-\s+)?(?:\d{3}|Hall|NB-|Lab|\d{1,2}:\d{2})',
                    # Pattern 5: Single name patterns (for cases where only last name is given)
                    r'\b([A-Z][a-z]{3,})\s+(?:-\s+)?(?:\d{3}|Hall|Lab|\d{1,2}:\d{2})',
                ]
                
                for pattern in faculty_patterns:
                    faculty_match = re.search(pattern, line)
                    if faculty_match:
                        potential_faculty = faculty_match.group(1).strip()
                        # Filter out common non-faculty words
                        exclude_words = ['Hall', 'Lab', 'Room', 'AM', 'PM', 'SZABIST', 'University', 'Campus', 
                                       'Design', 'Analysis', 'Data', 'Computer', 'Assessment', 'Techniques',
                                       'Management', 'Development', 'Research', 'International', 'Strategic',
                                       'Marketing', 'Accounting', 'Business', 'Applied', 'Introduction',
                                       'Fundamentals', 'Advanced', 'Principles', 'Ethics', 'Corporate']
                        if not any(word in potential_faculty for word in exclude_words):
                            faculty = potential_faculty
                            break
            else:
                # For cancelled classes, try to extract faculty before "Cancelled"
                # Enhanced to handle full names like "Dr. Muhammad Abo-Ul-Hassan Rashid"
                cancelled_faculty_patterns = [
                    r'(Dr\.\s+[A-Za-z\-\s\.]+?)\s+Cancelled',  # Dr. Full Name Cancelled
                    r'(Prof\.\s+[A-Za-z\-\s\.]+?)\s+Cancelled',  # Prof. Full Name Cancelled  
                    r'([A-Z][a-z]+(?:\s+[A-Za-z\-]+)*)\s+Cancelled',  # Name Cancelled (no title)
                ]
                
                faculty = "CANCELLED"  # Default value
                
                for pattern in cancelled_faculty_patterns:
                    cancelled_faculty_match = re.search(pattern, line, re.IGNORECASE)
                    if cancelled_faculty_match:
                        potential_faculty = cancelled_faculty_match.group(1).strip()
                        # Make sure it's not just the word "Cancelled" itself
                        if potential_faculty.lower() != 'cancelled' and len(potential_faculty) > 3:
                            faculty = potential_faculty
                            break
            
            # Extract time - Enhanced to handle various formats
            time = None
            if not is_cancelled:
                time_patterns = [
                    # Standard format: "08:00 AM - 09:30 AM"  
                    r'(\d{1,2}:\d{2}\s*[AP]M\s*(?:-|–|—)\s*\d{1,2}:\d{2}\s*[AP]M)',
                    # Single time: "08:00 AM"
                    r'(\d{1,2}:\d{2}\s*[AP]M)',
                ]
                
                for pattern in time_patterns:
                    time_match = re.search(pattern, line)
                    if time_match:
                        time = time_match.group(1).strip()
                        time = re.sub(r'\s+', ' ', time)  # Clean up spacing
                        break
            else:
                # For cancelled classes, time might be on a separate line or after date
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M\s*(?:-|–|—)\s*\d{1,2}:\d{2}\s*[AP]M)', line)
                if time_match:
                    time = time_match.group(1).strip()
                else:
                    time = "CANCELLED"
            
            # Extract room - Enhanced to handle various formats
            room = None
            if not is_cancelled:
                room_patterns = [
                    r'\b(TV\s+Studio)\b',             # "TV Studio"
                    r'\b(Media\s+Lab)\b',             # "Media Lab"  
                    r'\b(Digital\s+Lab)\b',           # "Digital Lab"
                    r'\b(Hall\s+\d+\s*[A-Z]?)\b',    # "Hall 01 A"
                    r'\b(NB-\d+)\b',                  # "NB-206"
                    r'\b(Lab\s+\d+)\b',               # "Lab 02" 
                    r'\b(\d{3})\s+\d{1,2}:\d{2}',    # "305" before time
                    r'\s(\d{3})\s',                   # "305" with spaces
                ]
                
                for pattern in room_patterns:
                    room_match = re.search(pattern, line)
                    if room_match:
                        room = room_match.group(1).strip()
                        break
            else:
                room = "CANCELLED"
            
            # Extract campus (usually at the end)
            campus = None
            campus_match = re.search(r'(SZABIST[^$]+)$', line)
            if campus_match:
                campus = campus_match.group(1).strip()
            elif not is_cancelled:
                campus = "SZABIST University Campus"  # Default campus
            else:
                campus = "CANCELLED"
            
            # Determine program from semester pattern
            program = None
            if semester:
                if semester.startswith('BS'):
                    program = 'BS'
                elif semester.startswith('MS'):
                    program = 'MS' 
                elif semester.startswith('PhD'):
                    program = 'PhD'
                elif 'EMBA' in semester or 'PMBA' in semester or 'MBA' in semester:
                    program = 'MBA'
                elif semester.startswith('BBA'):
                    program = 'BBA'
                elif semester.startswith('MMS'):
                    program = 'MMS'
                elif 'MHRM' in semester:
                    program = 'MHRM'
                elif 'MPM' in semester:
                    program = 'MPM'
                else:
                    program = 'Unknown'
            
            # Create the parsed item
            parsed_item = {
                'sr_no': sr_no,
                'dept': dept,
                'program': program,
                'semester': semester,
                'course': course,
                'course_title': course_title,
                'faculty': faculty,
                'room': room,
                'time': time,
                'campus': campus,
                'raw_line': line[:100] + ('...' if len(line) > 100 else '')  # For debugging
            }
            
            # Special handling for cancelled classes - still return them but mark as cancelled
            if is_cancelled and semester and course:
                logger.info(f"⚠️ Cancelled class parsed: {course} - {semester} - {faculty}")
                return parsed_item
            elif semester and course:
                logger.debug(f"✅ Successfully parsed: {course} - {semester} - Faculty: {faculty} - Time: {time}")
                return parsed_item
            else:
                logger.debug(f"❌ Missing essential fields - semester: {semester}, course: {course}")
                return None
                
        except Exception as e:
            logger.warning(f"❌ Failed to parse entry: {line[:50]}... Error: {e}")
            return None
    
    def normalize_column_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize and map column headers to standard names"""
        df_copy = df.copy()
        column_mapping = {}
        
        for col in df_copy.columns:
            col_str = str(col).strip()
            best_match = self.find_best_column_match(col_str)
            if best_match:
                column_mapping[col] = best_match
                logger.debug(f"📝 Mapped column '{col}' -> '{best_match}'")
        
        # Rename columns
        df_copy = df_copy.rename(columns=column_mapping)
        
        # If we don't have standard column names, try to infer from position
        if 'semester' not in df_copy.columns or 'course_code' not in df_copy.columns:
            df_copy = self._infer_columns_by_position(df_copy)
        
        return df_copy
    
    def _infer_columns_by_position(self, df: pd.DataFrame) -> pd.DataFrame:
        """Infer column types based on typical timetable structure"""
        df_copy = df.copy()
        cols = list(df_copy.columns)
        
        # Common timetable column order patterns
        standard_names = ['sr_no', 'dept', 'program', 'semester', 'course_code', 'course_title', 'faculty', 'room', 'time', 'campus']
        
        # Map by position if we have enough columns
        if len(cols) >= 6:
            new_mapping = {}
            for i, std_name in enumerate(standard_names[:len(cols)]):
                if i < len(cols):
                    new_mapping[cols[i]] = std_name
            
            df_copy = df_copy.rename(columns=new_mapping)
            logger.info(f"🔄 Inferred columns by position: {list(new_mapping.values())}")
        
        return df_copy
    
    def filter_by_semester(self, df: pd.DataFrame, target_semesters: List[str]) -> pd.DataFrame:
        """Filter dataframe by target semesters"""
        if not target_semesters:
            return df
        
        # Normalize target semesters
        target_normalized = [self._normalize_semester(sem) for sem in target_semesters]
        
        # Find semester column
        semester_col = None
        for col in df.columns:
            if 'semester' in str(col).lower() or 'class' in str(col).lower() or 'section' in str(col).lower():
                semester_col = col
                break
        
        if not semester_col:
            logger.warning("⚠️ No semester column found for filtering")
            return df
        
        # Filter rows
        mask = df[semester_col].astype(str).apply(
            lambda x: any(self._semester_matches(x, target) for target in target_normalized)
        )
        
        filtered_df = df[mask].copy()
        logger.info(f"🎯 Filtered from {len(df)} to {len(filtered_df)} rows for semesters: {target_semesters}")
        
        return filtered_df
    
    def _normalize_semester(self, semester: str) -> str:
        """Normalize semester string for comparison - ENHANCED for space variations"""
        if not semester:
            return ""
        
        # Remove extra spaces and normalize format
        normalized = re.sub(r'\s+', ' ', semester.strip())
        
        # Handle space variations between BS/MS and parentheses
        # Convert "BS (CS)" to "BS(CS)" and "BS(CS)" to "BS(CS)" (standardize to no space)
        normalized = re.sub(r'\b(BS|MS|PhD)\s+\(', r'\1(', normalized)
        
        # Fix parentheses
        normalized = re.sub(r'[\(\)]+', lambda m: '(' if '(' in m.group() else ')', normalized)
        
        # DO NOT normalize MSS to MS(SS) - they are different semesters!
        # MSS - 1 and MS(SS) - 1 are separate semesters that share classes
        # We need to preserve both as distinct semester identities
        
        return normalized
    
    def _semester_matches(self, semester_cell: str, target_semester: str) -> bool:
        """Check if a semester cell matches target semester with flexible spacing"""
        if not semester_cell or not target_semester:
            return False
        
        cell_normalized = self._normalize_semester(str(semester_cell))
        target_normalized = self._normalize_semester(target_semester)
        
        # Create flexible matching function that handles any spacing variation
        def flexible_match(cell_sem: str, target_sem: str) -> bool:
            # 1. Exact match first
            if cell_sem == target_sem:
                return True
            
            # 2. Compact match (remove all spaces) - handles "BS(CS)-2C" vs "BS (CS) - 2 C"
            cell_compact = re.sub(r'\s+', '', cell_sem)
            target_compact = re.sub(r'\s+', '', target_sem)
            if cell_compact == target_compact:
                return True
            
            # 3. Normalized section letter matching - handles "2C" vs "2 C"
            # Extract pattern: program (specialty) - number + section
            cell_pattern = re.match(r'^(.*?)\s*-\s*(\d+)\s*([A-Z]*)$', cell_sem)
            target_pattern = re.match(r'^(.*?)\s*-\s*(\d+)\s*([A-Z]*)$', target_sem)
            
            if cell_pattern and target_pattern:
                cell_program = re.sub(r'\s+', '', cell_pattern.group(1))  # Remove spaces from "BS(CS)"
                cell_number = cell_pattern.group(2)
                cell_section = cell_pattern.group(3)
                
                target_program = re.sub(r'\s+', '', target_pattern.group(1))
                target_number = target_pattern.group(2)
                target_section = target_pattern.group(3)
                
                # All components must match (program, number, section)
                if (cell_program == target_program and 
                    cell_number == target_number and 
                    cell_section == target_section):
                    return True
            
            return False
        
        # Check direct match
        if flexible_match(cell_normalized, target_normalized):
            return True
        
        # Handle slash-separated semesters (e.g., "EMBA - 1 / PMBA - 1")
        if '/' in cell_normalized:
            # Split by slash and check each part
            semester_parts = [part.strip() for part in cell_normalized.split('/')]
            for part in semester_parts:
                part_normalized = self._normalize_semester(part)
                if flexible_match(part_normalized, target_normalized):
                    return True
        
        return False
    
    def _extract_matching_semester(self, semester_cell: str, target_semesters: List[str]) -> str:
        """Extract the specific matching semester from a slash-separated string"""
        if not semester_cell or not target_semesters:
            return semester_cell
        
        cell_normalized = self._normalize_semester(str(semester_cell))
        
        # If no slash, return as is
        if '/' not in cell_normalized:
            return semester_cell
        
        # Split by slash and find the matching part
        semester_parts = [part.strip() for part in cell_normalized.split('/')]
        
        for target in target_semesters:
            target_normalized = self._normalize_semester(target)
            target_compact = re.sub(r'\s+', '', target_normalized)
            
            for part in semester_parts:
                part_normalized = self._normalize_semester(part)
                part_compact = re.sub(r'\s+', '', part_normalized)
                
                # Check for exact match or compact match
                if (part_normalized == target_normalized or 
                    part_compact == target_compact):
                    return part  # Return the matching part
        
        # If no specific match found, return original
        return semester_cell
    
    def extract_schedule_data(self, df: pd.DataFrame, target_semesters: List[str] = None) -> List[Dict]:
        """Extract schedule data from normalized dataframe"""
        schedule_items = []
        
        for idx, row in df.iterrows():
            try:
                # Extract semester first to check for slash-separated values
                raw_semester = self._safe_extract(row, ['semester', 'class', 'section'])
                
                # Determine which semesters to create entries for
                semesters_to_create = []
                
                if target_semesters and raw_semester:
                    # Check if this is a combined semester that matches multiple targets
                    raw_normalized = self._normalize_semester(str(raw_semester))
                    
                    if '/' in raw_normalized:
                        # Split by slash and check each part - treat each as a separate semester
                        semester_parts = [part.strip() for part in raw_normalized.split('/')]
                        
                        for target in target_semesters:
                            target_normalized = self._normalize_semester(target)
                            target_compact = re.sub(r'\s+', '', target_normalized)
                            
                            for part in semester_parts:
                                part_normalized = self._normalize_semester(part)
                                part_compact = re.sub(r'\s+', '', part_normalized)
                                
                                # Check for exact match or compact match
                                if (part_normalized == target_normalized or 
                                    part_compact == target_compact):
                                    # Keep the original part (not normalized) to preserve semester identity
                                    # This allows both "MS(SS) - 1" and "MSS - 1" to be distinct
                                    if part.strip() not in semesters_to_create:
                                        semesters_to_create.append(part.strip())
                                    break
                    else:
                        # Single semester, check if it matches any target
                        filtered_semester = self._extract_matching_semester(raw_semester, target_semesters)
                        if filtered_semester:
                            semesters_to_create.append(filtered_semester)
                else:
                    # No filtering, use original semester
                    semesters_to_create.append(raw_semester)
                
                # Create an entry for each matching semester
                for semester in semesters_to_create:
                    if not semester:
                        continue
                        
                    # Extract data with fallbacks
                    item = {
                        'sr_no': self._safe_extract(row, ['sr_no', 'sr', 'serial', 0]),
                        'dept': self._safe_extract(row, ['dept', 'department']),
                        'program': self._safe_extract(row, ['program']),
                        'semester': semester,
                        'course': self._safe_extract(row, ['course_code', 'course', 'subject']),
                        'course_title': self._safe_extract(row, ['course_title', 'title', 'name']),
                        'faculty': self._safe_extract(row, ['faculty', 'teacher', 'instructor']),
                        'room': self._safe_extract(row, ['room', 'venue', 'location']),
                        'time': self._safe_extract(row, ['time', 'timing', 'schedule']),
                        'campus': self._safe_extract(row, ['campus', 'location']),
                        'credits': self._safe_extract(row, ['credits', 'cr']),
                    }
                    
                    # Clean and validate data
                    item = self._clean_extracted_data(item)
                    
                    # Only add if we have essential data
                    if item.get('course') and item.get('semester'):
                        schedule_items.append(item)
                        logger.debug(f"✅ Extracted: {item['course']} for {item['semester']}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to extract row {idx}: {e}")
                continue
        
        return schedule_items
    
    def _safe_extract(self, row: pd.Series, column_names: List) -> Optional[str]:
        """Safely extract value from row using multiple possible column names"""
        for col_name in column_names:
            try:
                if col_name in row.index:
                    value = row[col_name]
                    if pd.notna(value) and str(value).strip():
                        return str(value).strip()
                elif isinstance(col_name, int) and col_name < len(row):
                    value = row.iloc[col_name]
                    if pd.notna(value) and str(value).strip():
                        return str(value).strip()
            except:
                continue
        return None
    
    def _clean_extracted_data(self, item: Dict) -> Dict:
        """Clean and normalize extracted data"""
        # Clean None values
        for key in item:
            if item[key] in [None, 'None', 'nan', '']:
                item[key] = None
        
        # Normalize course codes
        if item.get('course'):
            item['course'] = re.sub(r'\s+', ' ', item['course']).strip()
        
        # Clean contaminated course titles
        if item.get('course_title'):
            course_title = str(item['course_title']).strip()
            
            # Remove trailing "Dr." or other faculty titles that got appended
            # This handles cases like "Theories of International Relations Dr." 
            # and "Quantitative Analysis for Decision Making Dr. Muhammad Shoaib"
            trailing_faculty_pattern = r'\s+(Dr\.?|Prof\.?|Mr\.?|Ms\.?|Miss)\.?(?:\s+[A-Za-z\s\.]+)?$'
            course_title = re.sub(trailing_faculty_pattern, '', course_title, flags=re.IGNORECASE)
            
            # Remove faculty names from course title (Dr., Prof., Mr., Ms., etc.)
            # Look for patterns like "Course Title Dr. Name" or "Course Title / Additional Course Dr. Name"
            faculty_pattern = r'\s+(Dr\.?|Prof\.?|Mr\.?|Ms\.?|Miss)\s+[A-Za-z\s\.]+$'
            course_title = re.sub(faculty_pattern, '', course_title, flags=re.IGNORECASE)
            
            # Remove additional course codes that got mixed in (e.g., "/ BA 5322 Financial Accounting...")
            # Pattern: "/ [A-Z]{2,4} \d{4} ..."
            additional_course_pattern = r'\s*/\s*[A-Z]{2,4}\s*\d{4}.*'
            course_title = re.sub(additional_course_pattern, '', course_title)
            
            # Clean up extra slashes and spaces
            course_title = re.sub(r'\s*/\s*$', '', course_title)  # Remove trailing slash
            course_title = re.sub(r'\s+', ' ', course_title).strip()  # Normalize spaces
            
            # If the title is too short (likely truncated), try to reconstruct from raw_line
            if len(course_title) < 5 and item.get('raw_line'):
                extracted_title = self._extract_course_title_from_raw(item['raw_line'], item.get('course', ''))
                if extracted_title and len(extracted_title) > len(course_title):
                    course_title = extracted_title
            
            item['course_title'] = course_title if course_title else None
        
        # Clean faculty names
        if item.get('faculty'):
            faculty = str(item['faculty']).strip()
            # Remove "CANCELLED" from faculty field
            if faculty.upper() == 'CANCELLED':
                item['faculty'] = 'CANCELLED'
            else:
                # Normalize faculty names
                faculty = re.sub(r'\s+', ' ', faculty).strip()
                item['faculty'] = faculty
        
        # Normalize times
        if item.get('time'):
            time_str = item['time']
            # Try to fix common time format issues
            time_str = re.sub(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', 
                            r'\1:\2 - \3:\4', time_str)
            item['time'] = time_str
        
        # Set default campus for numbered rooms
        if item.get('room') and not item.get('campus'):
            if re.match(r'^\d{3}$', str(item['room'])):
                item['campus'] = 'SZABIST University Campus'
        
        return item
    
    def _extract_course_title_from_raw(self, raw_line: str, course_code: str) -> str:
        """Extract course title from raw line when the parsed title is truncated"""
        if not raw_line or not course_code:
            return ""
        
        try:
            # Look for pattern: "COURSE_CODE Full Course Title (credits)" 
            # More flexible pattern to handle various formats
            patterns = [
                rf'{re.escape(course_code)}\s+([^(]+?)\s*\([^)]+\)',  # Standard format
                rf'{re.escape(course_code)}\s+([^/]+?)(?:\s*/|\s+(?:Dr\.|Prof\.|Mr\.|Ms\.))',  # Before slash or faculty
                rf'{re.escape(course_code)}\s+(.+?)(?:\s+\(\d+,\d+\))',  # Before credits pattern
            ]
            
            for pattern in patterns:
                match = re.search(pattern, raw_line, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    
                    # Clean up the title
                    # Remove credits info that might be included
                    title = re.sub(r'\s*\(\d+,\d+\).*', '', title)
                    
                    # Remove faculty names
                    faculty_pattern = r'\s+(Dr\.?|Prof\.?|Mr\.?|Ms\.?)\s+[A-Za-z\s\.]+$'
                    title = re.sub(faculty_pattern, '', title, flags=re.IGNORECASE)
                    
                    # Clean up extra spaces and slashes
                    title = re.sub(r'\s+', ' ', title).strip()
                    title = re.sub(r'\s*/\s*$', '', title)  # Remove trailing slash
                    
                    if len(title) > 3:  # Only return if we got a meaningful title
                        return title
                        
        except Exception as e:
            logger.debug(f"Failed to extract title from raw line: {e}")
            
        return ""
    
    def parse_timetable(self, html_content: str, target_semesters: List[str] = None) -> List[Dict]:
        """Main method to parse timetable from HTML"""
        logger.info("🚀 Starting advanced pandas-based table parsing")
        logger.info(f"🎯 Target semesters: {target_semesters}")
        
        try:
            # Extract tables
            tables = self.extract_tables_from_html(html_content)
            
            if not tables:
                logger.error("❌ No tables found in HTML content")
                return []
            
            all_schedule_items = []
            
            for i, table in enumerate(tables):
                logger.info(f"📊 Processing table {i+1}: shape {table.shape}")
                
                # Skip empty or too small tables
                if table.empty or len(table.columns) < 3:
                    logger.warning(f"⚠️ Skipping table {i+1}: too small")
                    continue
                
                # Normalize column headers
                normalized_table = self.normalize_column_headers(table)
                logger.info(f"📊 Normalized table {i+1} columns: {list(normalized_table.columns)}")
                
                # Filter by semesters if specified
                if target_semesters:
                    filtered_table = self.filter_by_semester(normalized_table, target_semesters)
                else:
                    filtered_table = normalized_table
                
                if filtered_table.empty:
                    logger.info(f"ℹ️ Table {i+1}: No matching semesters found")
                    continue
                
                # Extract schedule data
                schedule_items = self.extract_schedule_data(filtered_table, target_semesters)
                all_schedule_items.extend(schedule_items)
                
                logger.info(f"✅ Table {i+1}: Extracted {len(schedule_items)} schedule items")
            
            logger.info(f"🎯 Total extracted: {len(all_schedule_items)} schedule items")
            
            # Log what we found for debugging
            if all_schedule_items:
                semesters_found = list(set(item.get('semester') for item in all_schedule_items if item.get('semester')))
                logger.info(f"🔍 Semesters found: {semesters_found}")
                logger.info(f"🔍 Target semesters: {target_semesters}")
                
                # Check if we got what we expected
                if target_semesters and len(all_schedule_items) > 0:
                    expected_found = any(any(self._semester_matches(found, target) for target in target_semesters) for found in semesters_found)
                    if not expected_found:
                        logger.warning(f"⚠️ Expected semesters {target_semesters} but found {semesters_found}")
            
            return all_schedule_items
            
        except Exception as e:
            logger.error(f"❌ Advanced parser failed with error: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []


def parse_html_with_advanced_pandas(html_content: str, target_semesters: List[str] = None) -> List[Dict]:
    """
    Main function to parse HTML timetable using advanced pandas table extraction
    """
    parser = AdvancedTableParser()
    return parser.parse_timetable(html_content, target_semesters)


if __name__ == "__main__":
    # Test the parser
    test_html = """
    <table>
        <tr><th>Sr No</th><th>Dept</th><th>Program</th><th>Class/Section</th><th>Course</th><th>Faculty</th><th>Room</th><th>Time</th><th>Campus</th></tr>
        <tr><td>1</td><td>CS</td><td>BS(CS)</td><td>BS(CS) - 5B</td><td>CSC 2123</td><td>Dr. Aqeel Ahmed</td><td>301</td><td>02:00 PM - 03:30 PM</td><td>SZABIST University Campus</td></tr>
        <tr><td>2</td><td>CS</td><td>BS(CS)</td><td>BS(CS) - 5B</td><td>CSC 2205</td><td>Awais Mehmood</td><td>301</td><td>03:30 PM - 05:00 PM</td><td>SZABIST University Campus</td></tr>
    </table>
    """
    
    result = parse_html_with_advanced_pandas(test_html, ['BS(CS) - 5B'])
    for item in result:
        print(f"Course: {item['course']}, Time: {item['time']}, Room: {item['room']}")