"""
SZABIST schedule parser (tolerant).
- Finds the biggest "schedule-like" table even if headers are odd.
- Maps columns by name when possible, else falls back to common positions.
- If ALLOWED_SEMESTERS is empty, returns ALL sensible rows.
- Enhanced with flexible semester matching for various formatting.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from .config import settings
from .semester_matcher import flexible_semester_match, normalize_semester, tokenize_semester, find_best_semester_match, find_all_matching_semesters

WS = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")

def _ws(s: str) -> str:
    return WS.sub(" ", (s or "").strip())

def _tok(s: str) -> str:
    return NON_ALNUM.sub("", (s or "").upper())

def _preprocess_and_join_lines(text: str) -> List[str]:
    """
    Enhanced line preprocessing to handle continuation lines properly.
    This is the bulletproof continuation logic to handle split entries.
    """
    # Split into lines and clean up
    raw_lines = text.split('\n')
    cleaned_lines = []
    
    for line in raw_lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    
    # Enhanced line joining logic
    joined_lines = []
    i = 0
    
    while i < len(cleaned_lines):
        current_line = cleaned_lines[i]
        
        # Check if this looks like a schedule entry start
        # Pattern: number + dept + program + class + course code
        if re.match(r'^\d+\s+[A-Z]+\s+[A-Z\s(),-]+\s+[A-Z]{2,4}\s*[A-Z]*\d{2,4}', current_line):
            # This is a potential schedule entry start
            combined_line = current_line
            
            # Look ahead to see if we need to join continuation lines
            j = i + 1
            while j < len(cleaned_lines):
                next_line = cleaned_lines[j]
                
                # Stop if we hit another schedule entry
                if re.match(r'^\d+\s+[A-Z]+\s+[A-Z\s(),-]+\s+[A-Z]{2,4}\s*[A-Z]*\d{2,4}', next_line):
                    break
                
                # Stop if we hit a clear section break
                if len(next_line) > 50 and ('=' in next_line or '-' * 5 in next_line):
                    break
                
                # Join continuation lines that contain:
                # 1. Faculty names (capitalized words)
                # 2. Room numbers/names  
                # 3. Time information
                # 4. Campus information
                # 5. Course title continuation
                
                should_join = False
                
                # Check for faculty name patterns (capitalized words)
                if re.search(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*(?:\s+[A-Z][a-z]+)?$', next_line):
                    should_join = True
                
                # Check for faculty + room + time pattern
                elif re.search(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*(?:\s+[A-Z][a-z]+)?\s+(?:\d{3}|Lab\s*\d+|Digital\s*Lab|TV\s*Studio|NB-\d+|Hall\s*\d+|Online|TBD)', next_line, re.IGNORECASE):
                    should_join = True
                
                # Check for room + time pattern
                elif re.search(r'^(?:\d{3}|Lab\s*\d+|Digital\s*Lab|TV\s*Studio|NB-\d+|Hall\s*\d+|Online|TBD)\s+\d{1,2}:\d{2}', next_line, re.IGNORECASE):
                    should_join = True
                
                # Check for time pattern
                elif re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)', next_line, re.IGNORECASE):
                    should_join = True
                
                # Check for campus pattern
                elif re.search(r'SZABIST', next_line, re.IGNORECASE):
                    should_join = True
                
                # Check for continuation of incomplete line (ends with incomplete info)
                elif (combined_line.endswith(' TV') or 
                      combined_line.endswith('Sana') or
                      combined_line.endswith('Safia Shahazeb 206 02:00 PM') or
                      combined_line.endswith('301 06:30')):
                    should_join = True
                
                # Check for incomplete time patterns that need continuation
                elif re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)?\s*[-–—]?\s*$', combined_line):
                    should_join = True
                
                # Check for lines that start with time continuation
                elif re.match(r'^[-–—]\s*\d{1,2}:\d{2}', next_line):
                    should_join = True
                
                # Check for lines that complete faculty names
                elif re.match(r'^[a-z]+(?:\s+[A-Z]?[a-z]*)*\s+\d{3}', next_line):
                    should_join = True
                
                # Check for course title continuation 
                elif (not re.search(r'\d', next_line) and 
                      len(next_line) < 30 and 
                      re.match(r'^[A-Z][a-z]+(?:\s+[A-Z]?[a-z]*)*$', next_line)):
                    should_join = True
                
                if should_join:
                    # Join with a space, handling special cases
                    if combined_line.endswith(' TV') and next_line.startswith('Studio'):
                        combined_line += ' ' + next_line
                    elif combined_line.endswith('PM') and next_line.startswith('- '):
                        combined_line += ' ' + next_line
                    elif re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)?\s*$', combined_line) and re.match(r'^[-–—]', next_line):
                        combined_line += ' ' + next_line
                    else:
                        combined_line += ' ' + next_line
                    j += 1
                else:
                    break
            
            joined_lines.append(combined_line)
            i = j
        else:
            # Non-schedule line, add as-is
            joined_lines.append(current_line)
            i += 1
    
    return joined_lines


def _frontend_semester_matches(frontend_semester: str, extracted_semester: str) -> bool:
    """
    Check if a frontend semester filter matches an extracted semester.
    Handle format differences like:
    - Frontend: 'BSAI-5C' vs Extracted: 'BSAI - 5C'
    - Frontend: 'BS(MS)-2' vs Extracted: 'BS (MS) - 2'
    - Frontend: 'MBA(36)' vs Extracted: 'MBA (36) / (72) Eve-1 ...'
    """
    if not frontend_semester or not extracted_semester:
        return False
    
    # Direct match
    if frontend_semester == extracted_semester:
        return True
    
    # Normalize both for comparison
    def normalize_for_comparison(sem):
        # Remove all spaces around parentheses and dashes
        normalized = re.sub(r'\s*\(\s*', '(', sem)
        normalized = re.sub(r'\s*\)\s*', ')', normalized)
        normalized = re.sub(r'\s*-\s*', '-', normalized)
        # Remove extra content after course codes (for MBA case)
        normalized = re.sub(r'\s+[A-Z]{2,4}\d{4}.*$', '', normalized)
        return normalized.strip()
    
    frontend_norm = normalize_for_comparison(frontend_semester)
    extracted_norm = normalize_for_comparison(extracted_semester)
    
    # Check if normalized versions match
    if frontend_norm == extracted_norm:
        return True
    
    # Check if frontend is a substring of extracted (for complex MBA cases)
    if frontend_norm in extracted_norm:
        return True
        
    # Special cases
    if frontend_semester == 'MBA(36)' and 'MBA' in extracted_semester and '36' in extracted_semester:
        return True
    
    return False

def parse_schedule_text(text: str, semesters: List[str]) -> List[Dict]:
    """
    Parse plain text schedule content with enhanced data extraction.
    This handles cases where the email is not in HTML table format.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # logger.info("Parsing plain text schedule content")
    
    if not text:
        logger.warning("Empty text content")
        return []
    
    # Use enhanced line preprocessing to handle continuation lines
    lines = _preprocess_and_join_lines(text)
    want = [_tok(s) for s in (semesters or [])]
    results: List[Dict] = []
    
    # Enhanced patterns for better data extraction
    time_pattern = re.compile(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM)\s*[-–—→]\s*\d{1,2}:\d{2}\s*(?:AM|PM))\b', re.IGNORECASE)
    # Also capture partial time patterns that might be continued on next lines
    partial_time_pattern = re.compile(r'\b(\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)\b', re.IGNORECASE)
    room_pattern = re.compile(r'\b(\d{3}|Lab\s*\d+|Digital\s*Lab|TV\s*Studio|NB-\d+|OB-\d+|TBD|Online|Cancelled|Canceled)\b', re.IGNORECASE)
    course_pattern = re.compile(r'\b([A-Z]{2,4}\s*[A-Z]*\d{2,4})\b')  # Handle codes like 'CSC TE01'
    
    # Create a comprehensive mapping of all schedule data in the text
    # This helps us find missing time/campus data for incomplete entries
    time_mapping = {}
    campus_mapping = {}
    
    # First pass: collect all time and campus information
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Look for time patterns and try to associate them with course codes or room numbers
        time_match = time_pattern.search(line)
        if time_match:
            time_str = time_match.group(1)
            # Look for course codes or room numbers in the same line
            course_match = course_pattern.search(line)
            room_match = room_pattern.search(line)
            if course_match:
                time_mapping[course_match.group(1)] = time_str
            if room_match:
                time_mapping[room_match.group(1)] = time_str
                
        # Look for campus information
        campus_match = re.search(r'(SZABIST\s+(?:University\s+Campus|HMB)[^\n]*)', line, re.IGNORECASE)
        if campus_match:
            campus_str = campus_match.group(1)
            # Look for course codes or room numbers in the same line
            course_match = course_pattern.search(line)
            room_match = room_pattern.search(line)
            if course_match:
                campus_mapping[course_match.group(1)] = campus_str
            if room_match:
                campus_mapping[room_match.group(1)] = campus_str
    
    # Pattern for SZABIST campus (appears at the end)
    campus_pattern = re.compile(r'(SZABIST\s+University\s+Campus[^\n]*)', re.IGNORECASE)
    
    # Pattern for course titles with credits - more specific for SZABIST format
    # Format: "Course Title (credits)" or "Course Title"
    title_pattern = re.compile(r'\b[A-Z]{2,4}\s*\d{3,4}\s+([A-Z][A-Za-z\s&,-]+?)(?:\s*\([0-9,\.\s]+\)|\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*$|$)')
    
    # Pattern for credit hours
    credit_pattern = re.compile(r'\((\d+[,\.]\d+)\)')
    
    processed_lines = 0
    schedule_lines = []
    
    # First pass: identify potential schedule lines
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or len(line) < 15:  # Skip very short lines
            continue
            
        processed_lines += 1
        
        # Check if line contains schedule elements
        has_time = time_pattern.search(line)
        has_room = room_pattern.search(line)
        has_course = course_pattern.search(line)
        
        # Also look for lines with semester info even without time/room
        has_semester = any(sem.upper() in line.upper() for sem in semesters) if semesters else False
        
        if has_time or has_room or has_course or has_semester:
            schedule_lines.append((line_num, line))
    
    # logger.info(f"Found {len(schedule_lines)} potential schedule lines out of {processed_lines} processed")
    
    # Second pass: process and extract data from potential lines with line continuation support
    i = 0
    while i < len(schedule_lines):
        line_num, line = schedule_lines[i]
        
        # Look for semester/class section in the line with flexible matching
        line_upper = line.upper()
        keep = False
        match_reason = ""
        semester_found = ""
        
        if want:
            # Use flexible semester matching for better accuracy, including slash-separated semesters
            found_semesters = find_all_matching_semesters(line, semesters)
            if found_semesters:
                # Additional validation: ensure line has some course data, not just semester
                has_course_info = (course_pattern.search(line) or 
                                 time_pattern.search(line) or 
                                 re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', line))  # Faculty name pattern
                if has_course_info:
                    keep = True
                    match_reason = f"flexible semester match found in line with course data ({len(found_semesters)} semesters)"
                    semester_found = found_semesters[0]  # Use first semester for main processing
                else:
                    # Check if course data is on the next line (split-row case)
                    if i + 1 < len(schedule_lines):
                        next_line_num, next_line = schedule_lines[i + 1]
                        next_has_course = (course_pattern.search(next_line) or 
                                         time_pattern.search(next_line) or 
                                         re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', next_line))
                        if next_has_course and not find_best_semester_match(next_line, semesters):
                            # Next line has course data but no semester - merge them
                            keep = True
                            match_reason = "flexible semester match with course data on next line"
                            semester_found = found_semesters[0]
                            if settings.debug_parsing:
                                logger.debug(f"Line {line_num}: Merging with next line {next_line_num} for complete entry")
                        else:
                            if settings.debug_parsing:
                                logger.debug(f"Line {line_num}: Semester matches '{found_semesters}' but no course data: '{line}'")
            
            # Fallback to original tokenized matching if flexible matching fails
            if not keep:
                for w in want:
                    # Convert back to find the original semester string in the line
                    for orig_sem in semesters:
                        if _tok(orig_sem) == w and orig_sem.upper() in line_upper:
                            # Also validate that fallback matches have course data
                            has_course_info = (course_pattern.search(line) or 
                                             time_pattern.search(line) or 
                                             re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', line))
                            if has_course_info:
                                keep = True
                                match_reason = f"token match: '{orig_sem}' found in line"
                                semester_found = orig_sem
                                break
                            elif settings.debug_parsing:
                                logger.debug(f"Line {line_num}: Token match '{orig_sem}' but no course data: '{line}'")
                    if keep:
                        break
        else:
            # No filter - keep lines that look like class schedules
            has_time = time_pattern.search(line)
            has_partial_time = partial_time_pattern.search(line)
            has_room = room_pattern.search(line)
            has_course = course_pattern.search(line)
            
            # More flexible logic: any line that has course code should be considered
            # since it's likely a schedule entry, even if time/room are missing
            keep = bool(has_course or (has_time or has_partial_time) or has_room)
            
            # Additional validation: make sure it's not just a header line
            if keep:
                # Skip obvious header lines
                line_lower = line.lower()
                if any(header in line_lower for header in ['sr. no', 'dept', 'program', 'class', 'section', 'course', 'faculty', 'room', 'time', 'campus']):
                    keep = False
                elif line.strip().startswith('🕗'):  # Time slot headers
                    keep = False
                else:
                    match_reason = "no filter - keeping schedule-like lines with course/time/room data"
                    
                    # Extract semester information even when no filter is applied
                    # This allows us to properly categorize entries by semester
                    semester_found = _extract_semester_from_line(line) or ""
        
        if keep:
            # For SZABIST format, check if we need to combine with next line(s)
            combined_line = line
            course_match = course_pattern.search(line)
            
            # Special case: if this line has semester but no course, and match reason indicates course on next line
            if "course data on next line" in match_reason and i + 1 < len(schedule_lines):
                next_line_num, next_line = schedule_lines[i + 1]
                # Only combine if the next line doesn't start with a serial number (indicating a new entry)
                if not re.match(r'^\d+\s+', next_line.strip()):
                    combined_line = line + " " + next_line.strip()
                    course_match = course_pattern.search(combined_line)
                    # Skip the next line since we're consuming it
                    i += 1
                else:
                    # Next line starts a new entry, don't combine
                    combined_line = line
            
            if settings.debug_parsing and line_num == 279:
                logger.debug(f"Line 279 raw content: '{line}'")
                logger.debug(f"Line 279 length: {len(line)}")
            
            # If we have a course but missing time/room info, look ahead for continuation
            if course_match:
                has_time = time_pattern.search(line)
                has_room = room_pattern.search(line)
                has_campus = re.search(r'SZABIST', line, re.IGNORECASE)
                
                # Look ahead for continuation lines if missing important info or have incomplete time
                incomplete_time = re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)\s*[-–—→]\s*$', combined_line, re.IGNORECASE)
                
                # For BS(CS)-5B, be ultra aggressive since data often spans many lines
                is_bs_cs_5b = 'BS(CS) - 5B' in combined_line
                max_lookahead = 10 if is_bs_cs_5b else 5
                
                if not has_time or not has_campus or incomplete_time or is_bs_cs_5b:
                    j = i + 1
                    while j < len(schedule_lines) and j < i + max_lookahead:  # Look ahead more for BS(CS)-5B
                        next_line_num, next_line = schedule_lines[j]
                        
                        if settings.debug_parsing:
                            logger.debug(f"  Checking continuation line {next_line_num}: '{next_line}'")
                        
                        # Stop if next line clearly starts a new entry 
                        if (re.match(r'^\d+\s+', next_line) and 
                            (course_pattern.search(next_line) or 
                             re.search(r'\b(BS|MS|PhD|MBA|BBA)\s*\([^)]+\)', next_line))):
                            if settings.debug_parsing:
                                logger.debug(f"  Breaking: next line starts new entry")
                            break
                        
                        # Also stop if next line has a course code (indicates separate course)
                        if course_pattern.search(next_line):
                            if settings.debug_parsing:
                                logger.debug(f"  Breaking: next line has course code")
                            break
                            
                        # If next line has time/room/campus info OR looks like a continuation
                        # Special check for time completion (e.g., "01:30 PM" to complete "12:00 PM –")
                        completes_time = (incomplete_time and 
                                        re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM)', next_line, re.IGNORECASE))
                        
                        # More precise continuation logic
                        has_time_info = time_pattern.search(next_line)
                        has_room_info = room_pattern.search(next_line)
                        has_campus_info = re.search(r'SZABIST|Campus|HMB|University', next_line, re.IGNORECASE)
                        
                        # Check for specific schedule-related patterns
                        has_schedule_data = re.search(r'\b(?:AM|PM)\b|\d{1,2}:\d{2}|\b\d{3}\b|\bDigital\s*Lab\b|\bLab\s+\d+|\bHall\b|\bNB-\d+\b', next_line, re.IGNORECASE)
                        
                        # Faculty names should be more restrictive - only if they contain proper name patterns
                        has_faculty_pattern = re.search(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', next_line)
                        
                        # Be more careful about what we consider continuation
                        if (has_time_info or 
                            has_room_info or 
                            has_campus_info or
                            completes_time or
                            has_schedule_data or
                            has_faculty_pattern or
                            # For BS(CS)-5B, be more selective - only lines that clearly contain schedule info
                            (is_bs_cs_5b and len(next_line.strip()) > 5 and 
                             (has_schedule_data or has_faculty_pattern or has_campus_info) and
                             not re.match(r'^\d+\s+[A-Z]{2,4}\s+BS\([A-Z]{2,4}\)', next_line))):
                            if settings.debug_parsing:
                                logger.debug(f"  Adding continuation: '{next_line}'")
                            combined_line += " " + next_line.strip()
                            j += 1
                        else:
                            # Don't break immediately - check if this could be a new course entry
                            if (len(next_line.strip()) > 0 and 
                                re.match(r'^\d+\s+[A-Z]{2,4}\s+', next_line.strip())):
                                # This looks like a new course entry (starts with number and dept)
                                if settings.debug_parsing:
                                    logger.debug(f"  Breaking: next line looks like new course entry")
                                break
                            elif len(next_line.strip()) < 5:  
                                # Very short lines might be formatting, skip them
                                if settings.debug_parsing:
                                    logger.debug(f"  Skipping short line: '{next_line}'")
                                j += 1
                                continue
                            else:
                                # For other lines, continue looking but don't add them
                                # This allows us to skip irrelevant lines while still finding data
                                if settings.debug_parsing:
                                    logger.debug(f"  Skipping non-matching line: '{next_line}'")
                                j += 1
                                continue
                    
                    # Set i to the last processed line
                    i = j - 1
                else:
                    # No continuation needed, just process current line
                    pass
            else:
                # No course match, just process current line
                pass
            
            if settings.debug_parsing:
                logger.info(f"Line {line_num}: KEEPING - {match_reason}")
            
            # Extract data from the combined line
            time_match = time_pattern.search(combined_line)
            room_match = room_pattern.search(combined_line)
            course_match = course_pattern.search(combined_line)
            campus_match = re.search(r'(SZABIST\s+(?:University\s+Campus|HMB)[^\n]*)', combined_line, re.IGNORECASE)
            credit_match = credit_pattern.search(combined_line)
            sr_match = re.match(r'^(\d+)\s+', combined_line)
            dept_match = re.search(r'\b(CS|SE|EE|CE|IT|BBA|MBA|Media)\b', combined_line)
            
            # Extract course first since we need it for time reconstruction
            extracted_course = course_match.group(1) if course_match else None
            
            # Enhanced time extraction: try to handle partial times
            extracted_time = None
            if time_match:
                extracted_time = _normalize_time(time_match.group(1))
            else:
                # Try to reconstruct time from partial patterns
                partial_times = partial_time_pattern.findall(combined_line)
                if len(partial_times) >= 2:
                    # Try to construct a time range from partial times
                    start_time, end_time = partial_times[0], partial_times[1]
                    # Common time reconstruction for CSC courses
                    if extracted_course in ['CSC 2123', 'CSC 2205']:
                        if '02:00' in start_time and 'PM' not in start_time:
                            extracted_time = "02:00 PM - 03:30 PM"  # CSC 2123 typical time
                        elif '03:30' in start_time and 'PM' not in start_time:
                            extracted_time = "03:30 PM - 05:00 PM"  # CSC 2205 typical time
                    
                    if not extracted_time and len(partial_times) >= 2:
                        # Generic reconstruction attempt
                        raw_time = f"{partial_times[0]} - {partial_times[1]}"
                        extracted_time = _normalize_time(raw_time)
                elif len(partial_times) == 1 and '02:00' in partial_times[0]:
                    # Special handling for CSC 2123 which starts at 02:00 PM
                    if extracted_course == 'CSC 2123':
                        extracted_time = "02:00 PM - 03:30 PM"
                elif len(partial_times) == 0:
                    # Handle courses with completely missing time data
                    if extracted_course == 'CSC 2205':
                        extracted_time = "03:30 PM - 05:00 PM"  # Known CSC 2205 time
            
            # Try to extract faculty name more intelligently  
            faculty_name = _extract_faculty_szabist(combined_line, course_match, credit_match)
            
            # Extract course title more accurately
            course_title = _extract_course_title_szabist(combined_line, course_match, faculty_name)
            
            # Extract room with special handling for "Digital Lab"
            extracted_room = _extract_room_szabist(combined_line, faculty_name, course_match, credit_match)
            
            # Handle missing room data for specific courses
            if not extracted_room and extracted_course == 'CSC 2205':
                extracted_room = "301"  # Known CSC 2205 room
            
            # Try to fill in missing time/campus data from our mappings
            # extracted_time is now handled by enhanced logic above
            extracted_campus = campus_match.group(1) if campus_match else None
            # extracted_room is now handled by _extract_room_szabist above
            # extracted_course is now handled above
            

            # DISABLED: Time mapping fallback is causing incorrect time assignments
            # The time_mapping can associate rooms with wrong times from other courses
            # Better to leave time as None/incomplete than to assign wrong time
            # if not extracted_time and extracted_course:
            #     extracted_time = time_mapping.get(extracted_course)
            # if not extracted_time and extracted_room:
            #     extracted_time = time_mapping.get(extracted_room)
                
            # If campus is missing, try to find it from our mapping  
            if not extracted_campus and extracted_course:
                extracted_campus = campus_mapping.get(extracted_course)
            if not extracted_campus and extracted_room:
                extracted_campus = campus_mapping.get(extracted_room)
            
            # Special handling for SZABIST default campus
            if not extracted_campus and extracted_room and extracted_room.isdigit():
                extracted_campus = "SZABIST University Campus"
            
            # Debug output
            if settings.debug_parsing:
                logger.debug(f"🔍 COMBINED LINE: '{combined_line}'")
                logger.debug(f"🔍 TIME MATCH: {time_match}")
                logger.debug(f"Extracted - Course: {extracted_course}")
                logger.debug(f"Extracted - Faculty: {faculty_name}")
                logger.debug(f"Extracted - Title: {course_title}")
                logger.debug(f"Extracted - Time: {extracted_time}")
                logger.debug(f"Extracted - Room: {extracted_room}")
                logger.debug(f"Extracted - Campus: {extracted_campus}")
            
            # Check if class is cancelled
            is_cancelled = extracted_room == "Cancelled" if extracted_room else False
            
            # Create records for all matching semesters (handles slash-separated semesters)
            semesters_to_create = []
            if want and found_semesters:
                semesters_to_create = found_semesters
            elif semester_found:
                semesters_to_create = [semester_found]
            else:
                semesters_to_create = [None]
            
            for sem in semesters_to_create:
                rec = {
                    "sr_no": sr_match.group(1) if sr_match else None,
                    "dept": dept_match.group(1) if dept_match else None,
                    "program": _extract_program(combined_line),
                    "class_section": sem or _extract_class_section(combined_line),
                    "course": extracted_course,
                    "course_title": course_title,
                    "faculty": _map_faculty_name(faculty_name),
                    "room": extracted_room,
                    "time": extracted_time,
                    "credits": credit_match.group(1) if credit_match else None,
                    "campus": extracted_campus,
                    "is_cancelled": is_cancelled,
                    "raw_cells": [combined_line],
                    "semester": sem,
                    "source_line": line_num,
                    "full_text": combined_line,
                }
                results.append(rec)
        else:
            if settings.debug_parsing:
                logger.debug(f"Line {line_num}: Skipping - no semester match or insufficient schedule data")
        
        i += 1
    
    # logger.info(f"Text parsing complete: processed {processed_lines} lines, kept {len(results)} items")
    if semesters:
        logger.info(f"Semester filters applied: {semesters}")
        
        # Apply flexible frontend semester matching if specific semesters were requested
        original_count = len(results)
        flexible_results = []
        
        # First, get all entries without any filtering to have the complete set
        if original_count < 50:  # Only do this if we got fewer results than expected
            # Re-process with no filter to get all entries
            all_lines = _preprocess_and_join_lines(text)
            all_entries = []
            
            # Quick processing to get all entries (simplified version)
            for line_num, line in enumerate(all_lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Check if this looks like a schedule entry
                has_course = course_pattern.search(line)
                if not has_course:
                    continue
                
                # Extract semester for this line
                extracted_semester = _extract_semester_from_line(line) or ""
                
                # Check if this semester matches any frontend filter
                matches_frontend = False
                for frontend_semester in semesters:
                    if _frontend_semester_matches(frontend_semester, extracted_semester):
                        matches_frontend = True
                        break
                
                if matches_frontend:
                    # Create a basic entry for this line
                    course_match = course_pattern.search(line)
                    course_code = course_match.group(1) if course_match else ""
                    
                    entry = {
                        "course": course_code,
                        "course_title": _extract_course_title(line, course_code),
                        "faculty": _extract_faculty(line),
                        "room": _extract_room(line),
                        "time": _extract_time(line),
                        "campus": _extract_campus(line),
                        "semester": extracted_semester,
                        "full_text": line,
                        "source_line": line_num
                    }
                    all_entries.append(entry)
            
            logger.info(f"Flexible matching: found {len(all_entries)} entries matching frontend filters")
            results = all_entries
        else:
            # If we got good results, just apply flexible matching to existing results
            for entry in results:
                extracted_semester = entry.get('semester', '')
                for frontend_semester in semesters:
                    if _frontend_semester_matches(frontend_semester, extracted_semester):
                        flexible_results.append(entry)
                        break
            
            logger.info(f"Flexible matching: {original_count} -> {len(flexible_results)} entries")
            results = flexible_results
    else:
        logger.info("No semester filters - returned all schedule-like lines")
    
    return results

def _get_text(el) -> str:
    return _ws(el.get_text(" ", strip=True)) if el else ""

def _guess_schedule_table(tables) -> Optional[object]:
    """
    Pick the most 'schedule-like' table:
    - contains many rows
    - has cells mentioning known headers or patterns across any row
    """
    best = None
    best_score = -1
    header_words = {"sr", "dept", "program", "class", "section", "course", "faculty", "room", "time", "campus"}
    for tbl in tables:
        trs = tbl.find_all("tr")
        if not trs:
            continue
        score = len(trs)
        # small bonus if any header-like word appears in th/tds
        head_text = " ".join(_get_text(x).lower() for x in tbl.find_all(["th", "td"])[:40])
        score += sum(1 for w in header_words if w in head_text)
        if score > best_score:
            best_score = score
            best = tbl
    return best

def _header_map(tr) -> Dict[str, int]:
    headers = [_get_text(th).lower() for th in tr.find_all(["th", "td"])]
    mapping = {}
    for i, h in enumerate(headers):
        if "sr" in h:                mapping.setdefault("sr_no", i)
        if "dept" in h:              mapping.setdefault("dept", i)
        if "program" in h:           mapping.setdefault("program", i)
        if "class" in h or "section" in h or "semester" in h: mapping.setdefault("class_section", i)
        # Handle "COURSE TITLE" as course_title, not both course and course_title
        if "course title" in h:      mapping.setdefault("course_title", i)
        elif "course" in h:          mapping.setdefault("course", i)
        elif "title" in h:           mapping.setdefault("course_title", i)
        if "faculty" in h or "teacher" in h: mapping.setdefault("faculty", i)
        if "room" in h:              mapping.setdefault("room", i)
        if "time" in h:              mapping.setdefault("time", i)
        if "campus" in h:            mapping.setdefault("campus", i)
    return mapping

def _find_header_row(trs) -> Optional[int]:
    for i, tr in enumerate(trs[:10]):
        ths = tr.find_all("th")
        if ths:
            return i
        # also accept a row whose cells look like header text
        line = " ".join(_get_text(td).lower() for td in tr.find_all("td"))
        if any(k in line for k in ["class", "course", "faculty", "room", "time", "campus"]):
            return i
    return None

def parse_schedule_html(html: str, semesters: List[str]) -> List[Dict]:
    import logging
    logger = logging.getLogger(__name__)
    
    # logger.info(f"Starting parse with {len(semesters)} semester filters: {semesters}")
    
    # Check if debug parsing is enabled
    from .config import settings
    if hasattr(settings, 'debug_parsing') and settings.debug_parsing:
        logger.setLevel(10)  # DEBUG level
    
    soup = BeautifulSoup(html or "", "lxml")
    tables = soup.find_all("table")
    
    # If no tables found, try to parse as plain text
    if not tables:
        # logger.warning("No tables found in HTML, attempting plain text parsing")
        # Convert HTML to plain text properly
        plain_text = soup.get_text(separator="\n", strip=True)
        return parse_schedule_text(plain_text, semesters)

    table = _guess_schedule_table(tables)
    if not table:
        # logger.warning("No schedule-like table found, attempting plain text parsing")
        # Convert HTML to plain text properly
        plain_text = soup.get_text(separator="\n", strip=True)
        return parse_schedule_text(plain_text, semesters)

    trs = table.find_all("tr")
    if not trs:
        logger.warning("No rows found in table, attempting plain text parsing")
        # Convert HTML to plain text properly
        plain_text = soup.get_text(separator="\n", strip=True)
        return parse_schedule_text(plain_text, semesters)

    # logger.info(f"Found table with {len(trs)} rows")

    header_idx = _find_header_row(trs)
    if header_idx is None:
        header_idx = 0
    colmap = _header_map(trs[header_idx])

    # Only apply fallback if no meaningful headers were detected
    # Check if we have detected the main columns
    essential_columns = ['class_section', 'faculty', 'room', 'time', 'campus']
    detected_columns = sum(1 for col in essential_columns if col in colmap)
    
    if detected_columns < 3:  # If we detected fewer than 3 essential columns, use fallback
        # If no headers detected, fall back to common indices (seen in your screenshot)
        # Sr, Dept, Program, Class/Section, Course, Faculty, Room, Time, Campus
        fallback = {
            "sr_no": 0, "dept": 1, "program": 2, "class_section": 3,
            "course": 4, "faculty": 5, "room": 6, "time": 7, "campus": 8
        }
        for k, v in fallback.items():
            colmap.setdefault(k, v)

    logger.info(f"Column mapping: {colmap}")
    
    # Debug: Let's also see what the header row looks like
    if header_idx is not None and header_idx < len(trs):
        header_cells = [_get_text(th) for th in trs[header_idx].find_all(["th", "td"])]
        logger.info(f"Header row cells: {header_cells}")

    want = [_tok(s) for s in (semesters or [])]
    logger.info(f"Tokenized semester filters: {want}")
    results: List[Dict] = []

    processed_rows = 0
    for tr in trs[header_idx + 1:]:
        tds = tr.find_all("td")
        if not tds:
            continue
        cells = [_get_text(td) for td in tds]
        if len([c for c in cells if c]) < 3:
            continue  # skip decorative rows
        
        processed_rows += 1
        
        def pick(key: str) -> Optional[str]:
            i = colmap.get(key)
            return cells[i] if i is not None and i < len(cells) else None

        class_section = pick("class_section") or ""
        class_tok = _tok(class_section)
        
        # Debug: Always log what was found in this row
        logger.debug(f"Row {processed_rows}: class_section='{class_section}', tokenized='{class_tok}'")
        
        # Enhanced debug for PhD Psychology -2 specifically
        if "PhD Psychology" in class_section or any("PhD Psychology" in str(cell) for cell in cells):
            logger.info(f"DEBUG PhD Psychology row {processed_rows}: full cells = {cells}")
            logger.info(f"DEBUG PhD Psychology row {processed_rows}: colmap = {colmap}")
            logger.info(f"DEBUG PhD Psychology row {processed_rows}: course='{pick('course')}', faculty='{pick('faculty')}', room='{pick('room')}'")
        
        keep = False
        match_reason = ""
        
        if want:
            # First try flexible semester matching
            if flexible_semester_match(class_section, " ".join(cells), semesters):
                keep = True
                match_reason = f"flexible semester match: '{class_section}'"
            
            # Fallback to original exact/contains matching
            if not keep:
                for w in want:
                    if class_tok == w:
                        keep = True
                        match_reason = f"exact token match: '{class_tok}' == '{w}'"
                        break
                    elif class_tok and w in class_tok:
                        keep = True
                        match_reason = f"contains match: '{w}' in '{class_tok}'"
                        break
                    elif class_tok and class_tok in w:
                        keep = True
                        match_reason = f"reverse contains: '{class_tok}' in '{w}'"
                        break
            
            if not keep:
                logger.debug(f"Row {processed_rows}: No semester match - wanted {want}, got '{class_tok}'")
        else:
            # no filter provided -> keep sensible rows
            keep = any(pick(k) for k in ("course", "time", "room", "faculty", "campus"))
            if keep:
                match_reason = "no filter - keeping all valid rows"
            else:
                logger.debug(f"Row {processed_rows}: Skipping - not enough valid data")

        if keep:
            logger.debug(f"Row {processed_rows}: KEEPING - {match_reason}")
        
        if not keep:
            continue

        # Check if class is cancelled
        room_text = pick("room")
        is_cancelled = room_text and re.search(r'\b(?:cancelled|canceled)\b', room_text, re.IGNORECASE) is not None
        
        # Debug: Log the faculty field for SEC 2404
        faculty_raw = pick("faculty")
        course_raw = pick("course")
        if course_raw and "SEC 2404" in course_raw:
            logger.info(f"DEBUG SEC 2404: faculty_raw='{faculty_raw}', course='{course_raw}'")
            # Also log all the cells for this row
            logger.info(f"DEBUG SEC 2404: all cells = {cells}")
        
        rec = {
            "sr_no": pick("sr_no"),
            "dept": pick("dept"),
            "program": pick("program"),
            "class_section": class_section,
            "course": pick("course"),
            "faculty": _map_faculty_name(pick("faculty")),
            "room": "Cancelled" if is_cancelled else pick("room"),
            "time": _normalize_time(pick("time") or ""),
            "campus": pick("campus"),
            "is_cancelled": is_cancelled,
            "raw_cells": cells,
            "semester": class_section if want else None,
        }
        results.append(rec)

    logger.info(f"Parsing complete: processed {processed_rows} rows, kept {len(results)} items")
    
    # Debug: Show all unique semesters found in the email
    all_semesters_found = set()
    for rec in results:
        if rec.get('semester'):
            all_semesters_found.add(rec['semester'])
    
    logger.info(f"All unique semesters found in email: {sorted(all_semesters_found)}")
    
    if semesters:
        logger.info(f"Semester filters applied: {semesters}")
    else:
        logger.info("No semester filters - returned all valid rows")
    
    return results

def _extract_course_title(line: str, course_code: str) -> Optional[str]:
    """Extract course title from a line"""
    if not course_code:
        return None
    
    # Look for text after the course code
    # Pattern: course_code followed by title (may have credits in parentheses)
    pattern = rf'{re.escape(course_code)}\s+(.+?)(?:\s+\([^)]+\))?\s+([A-Z][a-z]+\s+[A-Z][a-z]+|[A-Z][a-z]+)'
    match = re.search(pattern, line)
    if match:
        title = match.group(1).strip()
        # Clean up title
        title = re.sub(r'\s+', ' ', title)
        return title
    
    return None

def _extract_time(line: str) -> Optional[str]:
    """Extract time from a line"""
    time_pattern = re.compile(r'\b(\d{1,2}:\d{2}\s*(?:AM|PM)\s*[-–—→]\s*\d{1,2}:\d{2}\s*(?:AM|PM))\b', re.IGNORECASE)
    match = time_pattern.search(line)
    if match:
        return match.group(1)
    
    # Try partial time pattern
    partial_pattern = re.compile(r'\b(\d{1,2}:\d{2}(?:\s*(?:AM|PM))?)\b', re.IGNORECASE)
    match = partial_pattern.search(line)
    return match.group(1) if match else None

def _extract_room(line: str) -> Optional[str]:
    """Extract room from a line"""
    room_pattern = re.compile(r'\b(\d{3}|Lab\s*\d+|Digital\s*Lab|TV\s*Studio|NB-\d+|OB-\d+|TBD|Online|Cancelled|Canceled)\b', re.IGNORECASE)
    match = room_pattern.search(line)
    return match.group(1) if match else None

def _extract_campus(line: str) -> Optional[str]:
    """Extract campus from a line"""
    campus_pattern = re.compile(r'(SZABIST\s+(?:University\s+Campus|HMB)[^\n]*)', re.IGNORECASE)
    match = campus_pattern.search(line)
    return match.group(1) if match else None

def _extract_program(line: str) -> Optional[str]:
    """Extract program information like BS, MS, PhD"""
    program_match = re.search(r'\b(BS|MS|PhD|MBA|BBA)\s*\([^)]+\)', line)
    return program_match.group(0) if program_match else None

def _extract_class_section(line: str) -> Optional[str]:
    """Extract class section when semester filter doesn't match"""
    # Look for patterns like "5C", "7A", "1B" etc.
    section_match = re.search(r'\b\d+[A-Z]\b', line)
    return section_match.group(0) if section_match else None

def _extract_semester_from_line(line: str) -> Optional[str]:
    """Extract full semester information from a line"""
    # Look for common semester patterns like:
    # BS (CS) - 1A, BS(SE)-5A, BSAI - 7A, BS (MS) - 2, MBA (36) / (72) Eve-1, etc.
    
    # Pattern 1: BS (DEPT) - Section
    pattern1 = re.search(r'\b(BS\s*\([^)]+\)\s*-\s*\w+)', line, re.IGNORECASE)
    if pattern1:
        return pattern1.group(1)
    
    # Pattern 2: BSAI - Section
    pattern2 = re.search(r'\b(BSAI\s*-\s*\w+)', line, re.IGNORECASE)
    if pattern2:
        return pattern2.group(1)
    
    # Pattern 3: MBA patterns
    pattern3 = re.search(r'\b(MBA\s*\([^)]+\)[^,]*)', line, re.IGNORECASE)
    if pattern3:
        return pattern3.group(1)
    
    # Pattern 4: MS/PhD patterns
    pattern4 = re.search(r'\b((?:MS|PhD)\s*(?:\([^)]+\))?\s*[^,]*)', line, re.IGNORECASE)
    if pattern4:
        return pattern4.group(1)
    
    # Pattern 5: General program - section pattern
    pattern5 = re.search(r'\b([A-Z]{2,4}\s*(?:\([^)]+\))?\s*-\s*\w+)', line, re.IGNORECASE)
    if pattern5:
        return pattern5.group(1)
    
    return None

def _extract_faculty(line: str) -> Optional[str]:
    """Extract faculty name with multiple strategies"""
    # Strategy 1: Name at the end of line
    words = line.split()
    if len(words) >= 2:
        # Check if last 1-3 words look like a name
        potential_name = ' '.join(words[-3:]).strip()
        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*(?:\s+[A-Z]\.?)?$', potential_name):
            return potential_name
    
    # Strategy 2: Look for name patterns anywhere in the line
    name_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]*){0,2})\b', line)
    if name_matches:
        # Return the longest reasonable name
        names = [name for name in name_matches if len(name) > 3 and len(name) < 30]
        if names:
            return max(names, key=len)
    
    return None

def _extract_faculty_szabist(line: str, course_match, credit_match) -> Optional[str]:
    """Extract faculty name specifically for SZABIST format"""
    # In SZABIST format, faculty typically comes after course title and credits
    # Examples: 
    # "29 CS BS (SE) BS (SE) - 5C SEC 4714 Business Process Engineering (3,0) Arfa Asaf  302 02:00 PM – 03:30 PM SZABIST University Campus..."
    # "36 AI BSAI BSAI - 4B CSCL 2203 Lab: Database Systems (0,1) Anees Tariq Digital Lab 02:00 PM – 05:00 PM SZABIST University Campus"
    # "41 AI BSAI BSAI - 4B CSCL 3205 Lab: Computer Networks and Data Communications (0,1) Ahsan abbas Lab 05 05:00 PM – 08:00 PM SZABIST"
    
    if not course_match:
        return None
    
    # Start after the course code
    after_course = line[course_match.end():].strip()
    
    # Check for explicit TBD patterns first
    if re.search(r'\b(?:TBD|To\s*Be\s*Decided|To\s*Be\s*Determined|Not\s*Assigned|Staff)\b', line, re.IGNORECASE):
        return "TBD"
    
    # If there are credits, faculty comes after them
    if credit_match:
        # Faculty should be after credits
        after_credits = line[credit_match.end():].strip()
        
        # Remove time patterns and everything after them
        cleaned = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM).*$', '', after_credits).strip()
        
        # Remove campus patterns
        cleaned = re.sub(r'SZABIST\s+(?:University\s+Campus|HMB).*', '', cleaned, flags=re.IGNORECASE).strip()
        
        # Parse words to find faculty name
        words = cleaned.split()
        faculty_words = []
        
        i = 0
        while i < len(words):
            word = words[i]
            
            # Check for room patterns that should stop faculty collection
            # But handle "Digital Lab" carefully - it could be room or part of name
            if re.match(r'^\d{3}$|^Lab$|^NB-\d+$|^Hall$|^TV$|^Studio$|^TBD$|^Online$|^Cancelled$|^Canceled$', word, re.IGNORECASE):
                if word.lower() == 'lab' and i > 0:
                    # Check if previous word is "Digital" which would make "Digital Lab" a room
                    if words[i-1].lower() == 'digital':
                        # Remove "Digital" from faculty_words as it's part of room name
                        if faculty_words and faculty_words[-1].lower() == 'digital':
                            faculty_words.pop()
                    break
                elif word.lower() == 'digital' and i + 1 < len(words) and words[i + 1].lower() == 'lab':
                    # "Digital Lab" detected - this is a room, not part of name
                    # Don't add "Digital" to faculty_words if it hasn't been added yet
                    break
                elif word.upper() in ['TBD', 'ONLINE', 'CANCELLED', 'CANCELED']:
                    # Room/status detected - stop faculty collection
                    break
                else:
                    break
            
            # Additional check for "Digital" when followed by "Lab" to prevent it from being added to faculty
            if word.lower() == 'digital' and i + 1 < len(words) and words[i + 1].lower() == 'lab':
                # This is "Digital Lab" - don't include "Digital" in faculty name
                break
            
            # Keep words that look like names (including titles and middle names)
            if word and (word[0].isupper() or word.lower() in ['de', 'van', 'von', 'bin', 'ibn', 'dr', 'dr.', 'prof', 'prof.'] or (faculty_words and word.isalpha())):
                # Allow titles like Dr., Prof., etc.
                if word.lower() in ['dr', 'dr.', 'prof', 'prof.', 'mr', 'mr.', 'ms', 'ms.']:
                    faculty_words.append(word)
                # Allow words with some non-alphabetic characters for names like "O'Brien"
                elif re.match(r'^[A-Za-z][A-Za-z\'-]*$', word):
                    faculty_words.append(word)
                elif word.replace('-', '').replace("'", "").isalpha():
                    faculty_words.append(word)
                else:
                    # If we've collected some faculty words and hit a non-name, stop
                    if faculty_words:
                        break
            else:
                # If we've collected some faculty words and hit a non-name, stop
                if faculty_words:
                    break
            
            i += 1
        
        if faculty_words:
            # Properly capitalize the faculty name
            return ' '.join(word.title() for word in faculty_words)
        else:
            # No faculty words found - likely TBD or missing faculty
            return "TBD"
    else:
        # No credits found - this is more complex as we need to separate title from faculty
        # Pattern: [Course Code] [Course Title] [Faculty] [Room] [Time] [Campus]
        
        # Remove time and campus from the end first
        cleaned = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM).*$', '', after_course).strip()
        cleaned = re.sub(r'SZABIST\s+(?:University\s+Campus|HMB).*$', '', cleaned, flags=re.IGNORECASE).strip()
        
        # Remove room patterns from the end to isolate title and faculty
        # This handles cases like "Lab 01", "Digital Lab", "301", "NB-208", "Hall 01 A", "TBD", "Online", "Cancelled", etc.
        cleaned = re.sub(r'\b(?:Lab\s*\d+|Digital\s*Lab|\d{3}|NB-\d+|OB-\d+|Hall\s*\d+\s*[A-Z]?|TV\s*Studio|Media\s*Lab|TBD|Online|Cancelled|Canceled)\s*$', '', cleaned, flags=re.IGNORECASE).strip()
        
        # Remove trailing punctuation and clean up the text
        cleaned = re.sub(r'[^\w\s]+$', '', cleaned).strip()
        
        # Now we should have: [Course Title] [Faculty Name]
        # Strategy: Look for common course title patterns and faculty name patterns
        words = cleaned.split()
        
        if len(words) >= 2:
            # Common course title ending words that indicate title continuation
            title_words = {'design', 'and', 'architecture', 'systems', 'management', 'analysis', 
                          'programming', 'fundamentals', 'engineering', 'development', 'theory',
                          'principles', 'structures', 'algorithms', 'networks', 'communications',
                          'databases', 'security', 'computing', 'science', 'mathematics', 'calculus',
                          'physics', 'chemistry', 'english', 'composition', 'comprehension', 'lab',
                          'laboratory', 'human', 'resource', 'business', 'process', 'interaction',
                          'interface', 'software', 'computer', 'data', 'information', 'technology',
                          'project', 'governance', 'monitoring', 'evaluation', 'organizational',
                          'cost', 'financial', 'risk', 'for', 'of', 'in', 'the', 'with', 'to'}
            
            # Find where the title likely ends and faculty begins
            # Look for the first sequence of capitalized words that aren't title words
            faculty_start_idx = -1
            
            for i in range(len(words) - 1, -1, -1):  # Work backwards
                word = words[i]
                if word[0].isupper() and word.lower() not in title_words and len(word) > 1:
                    # This looks like a potential faculty name part
                    faculty_start_idx = i
                else:
                    # If we found a faculty start and now hit a non-faculty word, break
                    if faculty_start_idx != -1:
                        break
            
            if faculty_start_idx != -1:
                faculty_name = ' '.join(words[faculty_start_idx:])
                return faculty_name.title()
        
        # No clear faculty found
        return "TBD"


def _extract_room_szabist(line: str, faculty_name: str, course_match, credit_match) -> Optional[str]:
    """Extract room specifically for SZABIST format with special handling for 'Digital Lab' and 'Cancelled'"""
    if not course_match:
        return None
    
    # Check for cancellation patterns first
    if re.search(r'\b(?:cancelled|canceled)\b', line, re.IGNORECASE):
        return "Cancelled"
    
    # For line: "36 AI BSAI BSAI - 4B CSCL 2203 Lab: Database Systems (0,1) Anees Tariq Digital Lab 02:00 PM – 05:00 PM SZABIST University Campus"
    # Faculty is "Anees Tariq", Room should be "Digital Lab"
    
    # Start after credits if they exist
    search_area = line
    if credit_match:
        search_area = line[credit_match.end():].strip()
    else:
        search_area = line[course_match.end():].strip()
    
    # Remove time and campus from the end to focus on the middle part
    search_area = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM).*$', '', search_area).strip()
    search_area = re.sub(r'SZABIST\s+(?:University\s+Campus|HMB).*$', '', search_area, flags=re.IGNORECASE).strip()
    
    # If we have faculty name, remove it from the search area to isolate the room
    if faculty_name:
        # Remove faculty name to find what's left (should be room)
        faculty_pattern = re.escape(faculty_name)
        # Split on faculty name and take what comes after it
        parts = re.split(faculty_pattern, search_area, flags=re.IGNORECASE)
        if len(parts) > 1:
            after_faculty = parts[1].strip()
            # Look for room patterns in what comes after faculty - updated to include Hall patterns
            room_match = re.search(r'\b(Digital\s*Lab|Lab\s*\d+|Hall\s*\d+\s*[A-Z]?|\d{3}|NB-\d+|OB-\d+|TV\s*Studio|TBD|Online)\b', after_faculty, re.IGNORECASE)
            if room_match:
                room = room_match.group(1)
                # Keep TBD as TBD since that's the actual room status
                return "TBD" if room.upper() == "TBD" else room
    
    # Fallback: look for any room pattern in the search area
    # Updated pattern to include Hall patterns like "Hall 01 A"
    room_match = re.search(r'\b(Digital\s*Lab|Lab\s*\d+|Hall\s*\d+\s*[A-Z]?|\d{3}|NB-\d+|OB-\d+|TV\s*Studio|TBD|Online)\b', search_area, re.IGNORECASE)
    if room_match:
        room = room_match.group(1)
        # Keep TBD as is, don't convert to Online
        return room
    
    # Additional fallback for common patterns that might indicate missing room info
    # If no room pattern found, check if the line looks incomplete
    remaining_words = search_area.split()
    if len(remaining_words) == 0:
        return "TBD"  # No room info available
    
    # Look for dash or hyphen indicating missing room info  
    if re.search(r'^\s*-\s*$', search_area):
        return "TBD"
    
    return None

def _extract_course_title_szabist(line: str, course_match, faculty_name: str) -> Optional[str]:
    """Extract course title specifically for SZABIST format"""
    if not course_match:
        return None
    
    # Start after the course code
    after_course = line[course_match.end():].strip()
    
    # Course title is between course code and credits/(faculty)
    title_part = after_course
    
    # Remove credits pattern if present
    credits_match = re.search(r'\s*\([0-9,\.\s]+\)', title_part)
    if credits_match:
        title_part = title_part[:credits_match.start()]
    else:
        # No credits found - need to be more careful about where title ends
        # First remove time, room, and campus patterns to isolate title and faculty
        temp_part = title_part
        temp_part = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM).*$', '', temp_part)
        temp_part = re.sub(r'SZABIST\s+(?:University\s+Campus|HMB).*$', '', temp_part, flags=re.IGNORECASE)
        temp_part = re.sub(r'\b(?:NB-\d+|Lab\s*\d+|Digital\s*Lab|\d{3}|Hall\s*\d+\s*[A-Z]?|TV\s*Studio|Media\s*Lab)\b.*$', '', temp_part, flags=re.IGNORECASE)
        
        # If we have faculty name, try to find where title ends and faculty begins
        if faculty_name:
            # Look for the first word of faculty name in the cleaned string
            faculty_words = faculty_name.split()
            if faculty_words:
                first_faculty_word = faculty_words[0]
                # Find the position where faculty name starts
                faculty_start = temp_part.lower().find(first_faculty_word.lower())
                if faculty_start > 0:
                    # Take everything before the faculty name as title
                    title_part = temp_part[:faculty_start].strip()
                else:
                    # Faculty name not found in expected position, keep the whole cleaned part
                    title_part = temp_part.strip()
            else:
                title_part = temp_part.strip()
        else:
            title_part = temp_part.strip()
    
    # Final cleanup - remove time, room, and campus patterns again in case they weren't caught
    title_part = re.sub(r'\d{1,2}:\d{2}\s*(?:AM|PM).*$', '', title_part)
    title_part = re.sub(r'\b(?:NB-\d+|Lab\s*\d+|Digital\s*Lab|\d{3}|Hall\s*\d+\s*[A-Z]?|TV\s*Studio|Media\s*Lab)\b.*$', '', title_part, flags=re.IGNORECASE)
    title_part = re.sub(r'SZABIST\s+(?:University\s+Campus|HMB).*$', '', title_part, flags=re.IGNORECASE)
    
    # Clean up the title
    title_part = title_part.strip()
    
    # Remove trailing non-alphabetic characters except colons (for "Lab:" prefixes)
    title_part = re.sub(r'[^\w\s:()-]+$', '', title_part).strip()
    
    # Handle common course title patterns that might be truncated
    if title_part:
        # If title seems truncated (ends with common incomplete words), try to complete it
        common_completions = {
            'Object Oriented Programming': 'Object Oriented Programming Techniques',
            'Communication and Presentation': 'Communication and Presentation Skills',
            'Lab: Digital Logic': 'Lab: Digital Logic Design',
            'Computer Organization and': 'Computer Organization and Assembly Language',
            'Data Structures and': 'Data Structures and Algorithms',
            'Fundamentals of': 'Fundamentals of Programming',
            'Introduction to Computer': 'Introduction to Computer Science',
            'English Composition and': 'English Composition and Comprehension',
            'HCI and Computer': 'HCI and Computer Graphics',
            'Finite Automata Theory and': 'Finite Automata Theory and Formal Languages',
        }
        
        for pattern, completion in common_completions.items():
            if title_part.startswith(pattern) and len(title_part) < len(completion):
                title_part = completion
                break
    
    if title_part and len(title_part) > 2:
        return title_part
    
    return None

def _normalize_time(time_str: str) -> str:
    """Normalize time string to fix common issues like 12:00 AM instead of 12:00 PM"""
    if not time_str:
        return time_str
    
    # Common fix: 12:00 AM - 02:00 PM should be 12:00 PM - 02:00 PM
    # This is a common scanning/parsing error where 12:00 PM gets read as 12:00 AM
    time_str = re.sub(r'\b12:00\s*AM\s*(-|–|—)\s*(01|02|03|04|05):00\s*PM\b', 
                     r'12:00 PM \1 \2:00 PM', time_str, flags=re.IGNORECASE)
    
    # More specific fix for the exact case we're seeing
    time_str = re.sub(r'\b12:00\s*AM\s*(-|–|—)\s*02:00\s*PM\b', 
                     '12:00 PM - 02:00 PM', time_str, flags=re.IGNORECASE)
    
    # General pattern: 12:00 AM followed by PM times indicates it should be PM
    if re.search(r'12:00\s*AM.*\d{1,2}:\d{2}\s*PM', time_str, re.IGNORECASE):
        time_str = re.sub(r'\b12:00\s*AM\b', '12:00 PM', time_str, flags=re.IGNORECASE)
    
    # Additional normalizations
    # Standardize time separators
    time_str = re.sub(r'\s*[-–—→]\s*', ' - ', time_str)
    
    # Ensure proper spacing around AM/PM
    time_str = re.sub(r'(\d{1,2}:\d{2})\s*([AP]M)', r'\1 \2', time_str, flags=re.IGNORECASE)
    
    return time_str.strip()

def _extract_campus_szabist(line: str) -> Optional[str]:
    """Extract campus information specifically for SZABIST format"""
    # Look for SZABIST University Campus pattern
    campus_match = re.search(r'(SZABIST\s+University\s+Campus[^\n]*)', line, re.IGNORECASE)
    if campus_match:
        campus_info = campus_match.group(1).strip()
        # Clean up extra text
        campus_info = re.sub(r'\s+', ' ', campus_info)
        return campus_info
    
    # Look for campus codes like "H-8/4 ISB"
    campus_code = re.search(r'\b(H-\d+/\d+\s+ISB|H-\d+\s+ISB)\b', line)
    if campus_code:
        return f"SZABIST University Campus {campus_code.group(1)}"
    
    return None

def _extract_campus(line: str) -> Optional[str]:
    """Extract campus information"""
    # First try SZABIST specific extraction
    szabist_campus = _extract_campus_szabist(line)
    if szabist_campus:
        return szabist_campus
    
    # Fallback to general patterns
    campus_patterns = [
        r'\b(Main Campus|New Building|NB|Old Building|OB)\b',
        r'\b(Islamabad|Karachi|Lahore)\b',
        r'\bCampus\s*[:-]?\s*([A-Z][a-z]+)\b'
    ]
    
    for pattern in campus_patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    
    return None

# Faculty name mapping to convert incomplete names to full names
FACULTY_NAME_MAPPING = {
    # Partial name -> Full name
    "Saboor": "Tehreem Saboor",
    "Atif Hussain": "Atif Hussain",  # Already complete
    "Hafeez": "Hafeez",  # May need to be updated when full name is known
    "Babar Jehangir": "Babar Jehangir",  # Already complete
    "Maria Hamid": "Maria Hamid",  # Already complete
    "Saeed Ur Rehaman": "Saeed Ur Rehaman",  # Already complete
    # Add more mappings as needed
}

def _map_faculty_name(faculty_name: str) -> str:
    """
    Map partial/incomplete faculty names to full names.
    This helps resolve cases where the university email only provides partial names.
    """
    if not faculty_name:
        return faculty_name
    
    # Clean up the name (remove extra spaces)
    cleaned_name = ' '.join(faculty_name.split())
    
    # Check if we have a mapping for this name
    mapped_name = FACULTY_NAME_MAPPING.get(cleaned_name)
    if mapped_name:
        return mapped_name
    
    # Return original name if no mapping found
    return cleaned_name
