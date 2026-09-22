"""
Enhanced semester matching utilities for handling various formatting variations.
Handles cases like: BS(SE)-4A, BS (SE) - 4A, BS( SE)-  4A, etc.
"""

import re
from typing import List, Set

def normalize_semester(semester: str) -> str:
    """
    Normalize semester string by removing extra spaces and standardizing format.
    Examples:
    - 'BS (SE) - 4A' -> 'BS(SE)-4A'
    - 'BS( SE)-  4A' -> 'BS(SE)-4A'
    - 'BS(SE) - 4A' -> 'BS(SE)-4A'
    - 'BS (CS) - 1 D' -> 'BS(CS)-1D'
    """
    if not semester:
        return ""
    
    # Remove extra spaces around parentheses and dashes
    normalized = re.sub(r'\s*\(\s*', '(', semester)
    normalized = re.sub(r'\s*\)\s*', ')', normalized)
    normalized = re.sub(r'\s*-\s*', '-', normalized)
    
    # Remove spaces within section identifiers (e.g., "1 D" -> "1D")
    # This pattern looks for digit(s) followed by space(s) and letter(s) at the end
    normalized = re.sub(r'(\d+)\s+([A-Z]+)$', r'\1\2', normalized)
    
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single space
    
    return normalized.strip()

def tokenize_semester(semester: str) -> str:
    """
    Create a tokenized version for matching (removes all non-alphanumeric).
    Examples:
    - 'BS(SE)-4A' -> 'BSSE4A'
    - 'BS (SE) - 4A' -> 'BSSE4A'
    """
    return re.sub(r'[^A-Za-z0-9]', '', semester.upper())

def generate_semester_variations(semester: str) -> List[str]:
    """
    Generate common variations of a semester string for flexible matching.
    
    Args:
        semester: Base semester string like 'BS(SE)-4A'
    
    Returns:
        List of variations including different spacing patterns
    """
    if not semester:
        return []
    
    # First normalize the input
    base = normalize_semester(semester)
    
    # Extract components using regex - handle spaces in section part
    match = re.match(r'([A-Z]+)\(([A-Z]+)\)-?(\d+\s*[A-Z])', base.upper())
    if not match:
        # If it doesn't match expected pattern, return normalized version
        return [base]
    
    degree, specialization, section = match.groups()
    
    # Normalize section by removing any internal spaces (e.g., "1 D" -> "1D")
    section_normalized = re.sub(r'\s+', '', section)
    
    # Generate variations with both spaced and non-spaced section formats
    variations = [
        f"{degree}({specialization})-{section_normalized}",           # BS(SE)-4A
        f"{degree}({specialization}) - {section_normalized}",         # BS(SE) - 4A  
        f"{degree} ({specialization})-{section_normalized}",          # BS (SE)-4A
        f"{degree} ({specialization}) - {section_normalized}",       # BS (SE) - 4A
        f"{degree}( {specialization})-  {section_normalized}",       # BS( SE)-  4A
        f"{degree}( {specialization}) -  {section_normalized}",      # BS( SE) -  4A
        f"{degree}({specialization})- {section_normalized}",         # BS(SE)- 4A
        f"{degree} ({specialization})- {section_normalized}",        # BS (SE)- 4A
        # Also add variations with original spaced section if it was different
        f"{degree}({specialization})-{section}",           # BS(SE)-1 D (original format)
        f"{degree}({specialization}) - {section}",         # BS(SE) - 1 D  
        f"{degree} ({specialization})-{section}",          # BS (SE)-1 D
        f"{degree} ({specialization}) - {section}",       # BS (SE) - 1 D
    ]
    
    # Add the original and normalized versions
    variations.append(semester)
    variations.append(base)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)
    
    return unique_variations

def flexible_semester_match(target_semester: str, email_text: str, allowed_semesters: List[str]) -> bool:
    """
    Check if a target semester matches any allowed semester with flexible formatting.
    
    Args:
        target_semester: Semester string found in email (potentially with varied formatting)
        email_text: Full email text for context
        allowed_semesters: List of allowed semester patterns
    
    Returns:
        True if target_semester matches any allowed semester
    """
    if not target_semester or not allowed_semesters:
        return False

    # The surrounding line can contain several sections. Matching it here would
    # allow one permitted section to make every sibling section look permitted.
    # Keep the parameter for compatibility, but decide from the candidate itself.
    _ = email_text
    
    target_token = tokenize_semester(target_semester)
    
    # Check against all allowed semesters and their variations
    for allowed in allowed_semesters:
        allowed_token = tokenize_semester(allowed)
        
        # Direct token match
        if target_token == allowed_token:
            return True
        
        # Check if any variation of the allowed semester matches
        for variation in generate_semester_variations(allowed):
            if tokenize_semester(variation) == target_token:
                return True
        

    return False

def extract_all_semesters_from_line(line_text: str) -> List[str]:
    """
    Extract all semester patterns from a line, including slash-separated ones.
    
    Args:
        line_text: Text line to search for semesters
    
    Returns:
        List of all found semester strings
    """
    # Look for semester patterns, including slash-separated ones
    semester_patterns = [
        r'\b([A-Z]+\s*\(\s*[A-Z]+\s*\)\s*-?\s*\d+\s*[A-Z])\b',  # BS(SE)-4A variations
        r'\b([A-Z]+\s+[A-Z]+\s*-?\s*\d+\s*[A-Z])\b',            # Alternative formats
        r'\b([A-Z]{2,4}\s*-\s*\d+(?:\s*[A-Z])?)\b',             # MPM-1, EMBA-2, MS-1 formats
        r'\b([A-Z]+\s*\(\s*[A-Z]+\s*\)\s*-\s*\d+)\b',           # MS(DS)-1, MS(SS)-1 formats
    ]
    
    all_semesters = []
    
    # First, check if there are slash-separated semesters
    if '/' in line_text:
        # Split by slashes and extract semesters from each part
        parts = line_text.split('/')
        for part in parts:
            for pattern in semester_patterns:
                matches = re.findall(pattern, part.strip(), re.IGNORECASE)
                all_semesters.extend(matches)
    else:
        # Regular extraction
        for pattern in semester_patterns:
            matches = re.findall(pattern, line_text, re.IGNORECASE)
            all_semesters.extend(matches)
    
    return [normalize_semester(sem) for sem in all_semesters]

def find_all_matching_semesters(line_text: str, allowed_semesters: List[str]) -> List[str]:
    """
    Find ALL matching semesters from a line text based on allowed semesters.
    
    Args:
        line_text: Text line to search for semesters
        allowed_semesters: List of allowed semester patterns
    
    Returns:
        List of all matching semester strings
    """
    if not allowed_semesters:
        return []
    
    # Extract all semesters from the line
    found_semesters = extract_all_semesters_from_line(line_text)
    
    # Check which ones match the allowed semesters
    matching_semesters = []
    for found in found_semesters:
        if flexible_semester_match(found, line_text, allowed_semesters):
            matching_semesters.append(found)
    
    return matching_semesters

def find_best_semester_match(email_text: str, allowed_semesters: List[str]) -> str:
    """
    Find the best matching semester from email text based on allowed semesters.
    
    Args:
        email_text: Full email text to search
        allowed_semesters: List of allowed semester patterns
    
    Returns:
        Best matching semester string or empty string if none found
    """
    if not allowed_semesters:
        return ""
    
    # Look for semester patterns in the email
    semester_patterns = [
        r'\b([A-Z]+\s*\(\s*[A-Z]+\s*\)\s*-?\s*\d+\s*[A-Z])\b',  # BS(SE)-4A variations with optional spaces
        r'\b([A-Z]+\s+[A-Z]+\s*-?\s*\d+\s*[A-Z])\b',            # Alternative formats with optional spaces
        r'\b([A-Z]{2,4}\s*-\s*\d+(?:\s*[A-Z])?)\b',             # MPM-1, EMBA-2, MS-1 formats
        r'\b([A-Z]+\s*\(\s*[A-Z]+\s*\)\s*-\s*\d+)\b',           # MS(DS)-1, MS(SS)-1 formats
    ]
    
    found_semesters = []
    for pattern in semester_patterns:
        matches = re.findall(pattern, email_text, re.IGNORECASE)
        found_semesters.extend(matches)
    
    # Check each found semester against allowed semesters
    for found in found_semesters:
        if flexible_semester_match(found, email_text, allowed_semesters):
            return normalize_semester(found)
    
    # If no direct match, try partial matching
    for allowed in allowed_semesters:
        for variation in generate_semester_variations(allowed):
            if variation.upper() in email_text.upper():
                return normalize_semester(allowed)
    
    return ""
