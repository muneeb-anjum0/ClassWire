from scraper.timetable_parser import parse_html_with_advanced_pandas


def test_parser_avoids_department_noise_in_semester_display():
    email_body = (
        '20 Computer Sciences BSCS BCS/BS 8C CSC 4201 Information Security (3,0) '
        'Muhammad Taseer ul Islam 201 08:00 PM - 09:30 PM SZABIST University H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['semester_display'] == 'BCS/BS 8C'
    assert item['course_title'] == 'Information Security'
    assert item['faculty'] == 'Muhammad Taseer ul Islam'
    assert item['room'] == '201'


def test_parser_uses_headers_when_columns_are_reordered_and_serial_is_missing():
    html = """
    <table>
      <tr><th>Class Time</th><th>Teacher</th><th>Course Name</th><th>Section</th><th>Venue</th><th>Campus</th></tr>
      <tr><td>08:00 AM - 09:30 AM</td><td>Dr. Ada Lovelace</td><td>CSC 1001 Programming (3,0)</td><td>BS(CS)-1A</td><td>101</td><td>Main Campus</td></tr>
    </table>
    """

    items = parse_html_with_advanced_pandas(html)

    assert len(items) == 1
    assert items[0]["semester_display"] == "BS(CS)-1A"
    assert items[0]["course_code"] == "CSC 1001"
    assert items[0]["faculty"] == "Dr. Ada Lovelace"
    assert items[0]["room"] == "101"
    assert items[0]["time"] == "08:00 AM - 09:30 AM"


def test_parser_combines_multiple_timetable_tables_without_duplicate_nested_rows():
    html = """
    <div>
      <table>
        <tr><th>Sr.No</th><th>Department</th><th>Program</th><th>Section</th><th>Course Name</th><th>Faculty Name</th><th>Room</th><th>Class Time</th><th>Campus</th></tr>
        <tr><td>1</td><td>Computing</td><td>BSCS</td><td>BS(CS)-1A</td><td>CSC 1001 Programming (3,0)</td><td>Teacher One</td><td>101</td><td>08:00 AM - 09:30 AM</td><td>Main Campus</td></tr>
      </table>
      <table>
        <tr><th>S.No</th><th>Department</th><th>Program</th><th>Section</th><th>Course</th><th>Instructor</th><th>Location</th><th>Timing</th><th>Building</th></tr>
        <tr><td>1</td><td>Computing</td><td>BSCS</td><td>BS(CS)-2A</td><td>CSC 2001 Databases (3,0)</td><td>Teacher Two</td><td>202</td><td>09:30 AM - 11:00 AM</td><td>North Campus</td></tr>
      </table>
    </div>
    """

    items = parse_html_with_advanced_pandas(html)

    assert len(items) == 2
    assert {item["course_title"] for item in items} == {"Programming", "Databases"}


def test_parser_extracts_meeting_room_and_keeps_faculty_clean():
    email_body = (
        '58 Management Sciences PhDMS PhD-1 MS 6325 Seminars in Finance '
        'Dr. Shumaila Zeb Meeting Room Admin Block '
        '05:00 PM - 08:00 PM SZABIST University H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['semester_display'] == 'PhD-1'
    assert item['course_title'] == 'Seminars in Finance'
    assert item['faculty'] == 'Dr. Shumaila Zeb'
    assert item['room'] == 'Meeting Room Admin Block'


def test_parser_extracts_psy_lab_room():
    email_body = (
        '59 Social Sciences MS - CPY MS - CPY Open CLP 5103 Quantitative Research Methods (3,0) '
        'Maria Rafique Psy Lab 05:00 PM - 08:00 PM SZABIST University H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['semester_display'] == 'MS - CPY Open'
    assert item['faculty'] == 'Maria Rafique'
    assert item['room'] == 'Psy Lab'


def test_parser_handles_tuesday_time_without_meridiem():
    email_body = (
        '23\tComputer Sciences\tBSCS\tBSCS 5 A\tCSC 1215 Teachings of Holy Quran (0,0)\tMuhammad Hassaan Raza\tONLINE\t10:00 - 11:00\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1
    item = items[0]
    assert item['semester_display'] == 'BSCS 5 A'
    assert item['room'] == 'ONLINE'
    assert item['time'] == '10:00 - 11:00'


def test_parser_handles_cancelled_room_with_date_line():
    email_body = (
        '37\tSocial Sciences\tBSSS\tBSSS 2\tSS 1216 Intro to International Relations\tGulrukhsar Mujahid -\tCancelled\n30-04-2026\t08:00 AM - 11:00 AM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1
    item = items[0]
    assert item['semester_display'] == 'BSSS 2'
    assert item['room'].lower().startswith('cancelled')
    assert item['faculty'] == 'Gulrukhsar Mujahid'


def test_parser_handles_meeting_room_numbered_admin_block():
    email_body = (
        '49\tManagement Sciences\tPhDMS\tPhD-1\tMS 6432 Strategic Entrepreneurial Marketing\tDr. Fahim A Khan\tMeeting Room 1\nAdmin Block\t06:30 PM - 09:30 PM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1
    item = items[0]
    assert item['semester_display'] == 'PhD-1'
    assert item['faculty'] == 'Dr. Fahim A Khan'
    assert item['room'] == 'Meeting Room 1 Admin Block'


def test_parser_strips_faculty_prefix_from_room_values():
    email_body = (
        '50\tManagement Sciences\tPhDMS\tPhD-1\tMS 6432 Strategic Entrepreneurial Marketing\tDr. Fahim A Khan\tDr. Fahim A Khan 206\t06:30 PM - 09:30 PM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['faculty'] == 'Dr. Fahim A Khan'
    assert item['room'] == '206'


def test_parser_moves_leading_room_name_into_faculty():
    email_body = (
        '51\tComputer Sciences\tBSSE\tBSSE 5 A\tSECL 3604 Lab: Software Construction and Development (0,1)\tJawad\tNaseer Lab 01\t12:00 PM - 02:00 PM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['faculty'] == 'Jawad Naseer'
    assert item['room'] == 'Lab 01'


def test_parser_handles_conference_room_and_trailing_course_suffix():
    email_body = (
        '19\tManagement Sciences\tMSBA /MSMS\tMSMS /MSBA\tPerformance Management\tDr. Faisal Malik\tConference Room\t11:10 AM - 02:10 PM\tSZABIST University\nH-8/4 ISB Campus\n'
        '45\tMedia Sciences\tBS Media\tBS Media 4 B\tMD 2428 Introduction to Advertising Strategy (3,0) B\tDr. Naila\t208\t02:20 PM - 05:20 PM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 2
    by_row = {item['row_number']: item for item in items}

    assert by_row[19]['room'] == 'Conference Room'
    assert by_row[19]['faculty'] == 'Dr. Faisal Malik'
    assert by_row[45]['course_title'] == 'Introduction to Advertising Strategy'


def test_parser_strips_lab_prefix_from_course_titles():
    email_body = (
        '14\tComputer Sciences\tBSCS\tBSCS 2 C\tCSCL 1207 Lab: Digital Logic Design (0,1)\tShehwar Tanveer -\tLab 03\t08:00 AM - 10:00 AM\tSZABIST University\nH-8/4 ISB Campus\n'
        '29\tComputer Sciences\tBSSE\tBSSE Open\tCSCL 2102 Lab: Data Structures and Algorithms (0,1)\tAzhar Kamal -\tLab 01\t08:00 AM - 10:00 AM\tSZABIST University\nH-8/4 ISB Campus\n'
        '31\tRobotics & AI\tBSAI\tBSAI 1 C\tCSCL 1103 Lab: Fundamentals of Programming (0,1)\tAnnas Khalid Khan\tLab 05\t08:00 AM - 10:00 AM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 3
    by_row = {item['row_number']: item for item in items}

    assert by_row[14]['course_title'] == 'Digital Logic Design'
    assert by_row[29]['course_title'] == 'Data Structures and Algorithms'
    assert by_row[31]['course_title'] == 'Fundamentals of Programming'


def test_parser_splits_concatenated_course_code_and_title():
    email_body = (
        '39\tSocial Sciences\tBSSS\tBSSS 2 / BS Psychology 2\tSS 2413Philosphy\tDr. Muhammad Abo-Ul-Hassan Rashid\tAuditorium\t08:00 AM - 11:00 AM\tSZABIST University\nH-8/4 ISB Campus\n'
        '44\tMedia Sciences\tBS Media\tBS Media 4 B\tMD 2318 History of Commercial Art (3,0) B\tMasroor Ahmed\t206\t08:00 AM - 11:00 AM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 2
    by_row = {item['row_number']: item for item in items}

    assert by_row[39]['course_title'] == 'Philosphy'
    assert by_row[39]['course_code'] == 'SS 2413'
    assert by_row[44]['course_title'] == 'History of Commercial Art'


def test_parser_separates_course_title_from_faculty_in_flattened_rows():
    email_body = (
        '33\tSocial Sciences\tBSSS\tBSSS 4 / BS Psychology 4\tSS 2418 Statistical Inferences\tDr. Syed Aziz Rasool\t203\t05:30 PM - 08:30 PM\tSZABIST University\nH-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1
    item = items[0]
    assert item['semester_display'] == 'BS Psychology 4'
    assert item['course_title'] == 'Statistical Inferences'
    assert item['faculty'] == 'Dr. Syed Aziz Rasool'


def test_parser_normalizes_bs_psychology_variants_to_one_group():
    email_body = (
        '36 Social Sciences BSSS OPEN BSSS / BS Psychology 4 SS 4112 Developmental Psychology Abdul Hanan Sami 301 02:00 PM - 05:00 PM SZABIST University H-8/4 ISB Campus\n'
        '33 Social Sciences BSSS BSSS 4 / BS Psychology 4 SS 2418 Statistical Inferences Dr. Syed Aziz Rasool 203 05:30 PM - 08:30 PM SZABIST University H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 2
    assert {item['semester_display'] for item in items} == {'BS Psychology 4'}

    by_row = {item['row_number']: item for item in items}
    assert by_row[36]['course_title'] == 'Developmental Psychology'
    assert by_row[36]['faculty'] == 'Abdul Hanan Sami'
    assert by_row[33]['course_title'] == 'Statistical Inferences'
    assert by_row[33]['faculty'] == 'Dr. Syed Aziz Rasool'


def test_parser_handles_tuesday_batch_variants_from_provided_sample():
    email_body = (
        '38\tSocial Sciences\tBSSS & BS PSY\tBSSS 1  /  BS Psychology 1\tSS 1201 Introduction to Social Sciences\tAbdul Hanan Sami\t204\t08:00 AM - 11:00 AM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '39\tSocial Sciences\tBSSS & BS PSY\tBSSS 2 / BS Psychology 2\tSS 2413Philosphy\tDr. Muhammad Abo-Ul-Hassan Rashid\tAuditorium\t08:00 AM - 11:00 AM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '2\tManagement Sciences\tPhDMS\tPhD-1\tMS 6428 Global Marketing Strategies\tDr. Zoya Wajid Satti\tMeeting Room\n'
        'Admin Block\t06:30 PM - 09:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '44\tMedia Sciences\tBS Media\tBS Media 4 B\tMD 2318 History of Commercial Art (3,0) B\tMasroor Ahmed\t206\t08:00 AM - 11:00 AM\tSZABIST University\n'
        'H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 4

    by_row = {item['row_number']: item for item in items}

    assert by_row[38]['semester_display'] == 'BS Psychology 1'
    assert by_row[38]['course_title'] == 'Introduction to Social Sciences'

    assert by_row[39]['semester_display'] == 'BS Psychology 2'
    assert by_row[39]['course_code'] == 'SS 2413'
    assert by_row[39]['course_title'] == 'Philosphy'

    assert by_row[2]['semester_display'] == 'PhD-1'
    assert by_row[2]['room'] == 'Meeting Room Admin Block'

    assert by_row[44]['course_title'] == 'History of Commercial Art'


def test_parser_handles_flattened_bsss_open_row_without_swallowing_course_title():
    email_body = (
        '36 Social Sciences BSSS OPEN BSSS Open SS 4211 Psychological Testing Amber Gillani 204 05:30 PM - 08:30 PM SZABIST University H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 1

    item = items[0]
    assert item['semester_display'] == 'BSSS Open'
    assert item['course'] == 'SS 4211 Psychological Testing'
    assert item['course_title'] == 'Psychological Testing'
    assert item['faculty'] == 'Amber Gillani'
    assert item['room'] == '204'


def test_parser_normalizes_split_semester_variants_listed_by_user():
    email_body = (
        '1\tManagement Sciences\tBS (AF)\tBS (AF) 6 A /\nBS (AF) 4 A\tAF 3503 Business Ethics (3,0)\tDr. Fuwad Bashir Awan\t205\t02:20 PM - 05:20 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '2\tManagement Sciences\tBSBA\tBS Media 4 A / 4 B\tMD 1119 Play Analysis (3,0)\tLeyla Zuberi\t206\t11:10 AM - 02:10 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '3\tSocial Sciences\tBSSS OPEN\tBSSS 1  /\nBS Psychology 1\tSS 1201 Introduction to Social Sciences\tAbdul Hanan Sami\t204\t08:00 AM - 11:00 AM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '4\tSocial Sciences\tBSSS OPEN\tBSSS 3 /\nBS Psychology3\tSS 2318 Mathematics and Statistics\tDr. Syed Aziz Rasool\t208\t11:10 AM - 02:10 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '5\tSocial Sciences\tBSSS OPEN\tBSSS 2 /\nBS Psychology 2\tSS 2413Philosphy\tDr. Muhammad Abo-Ul-Hassan Rashid\tAuditorium\t08:00 AM - 11:00 AM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '6\tSocial Sciences\tBS (Psychology)\tBS (Psychology) 2\tInternational Law and Human Rights\tDr. Syed Adnan Ali Shah Bukhari\t302\t02:20 PM - 05:20 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '7\tSocial Sciences\tBSSS OPEN\tBSSS /\nBS Psychology 4\tSS 4112 Developmental Psychology\tAbdul Hanan Sami\t301\t02:00 PM - 05:00 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '8\tManagement Sciences\tBS (AF)\tBS (AF) 4 A /\nBS (AF) 8 A\tAF 2411 Entrepreneurship (3,0)\tMuhammad Ijaz Minhas\t102\t05:30 PM - 08:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '9\tComputer Sciences\tMS Cyber Security / MS Computer Science\tMS Cyber Security - 1 / MS Computer Science\tCYS 5103 Network Security (3,0)\tMuhammad Akram Mughal\t306\t06:30 PM - 09:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '10\tComputer Sciences\tMS Cyber Security\tMS Cyber Security - 2\tCYS 5233 Machine Learning for Cyber Security (3,0)\tDr. Qamar Abbas\tHall 01 A\t06:30 PM - 09:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '11\tComputer Sciences\tMS Computer Science\tMS Computer Science\tCSC 5202 Advanced Computer Architecture (3,0)\tDr. Danish Mahmood\t105\t06:30 PM - 09:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '12\tRobotics & AI\tMS(Data Sci)\tMS(Data Sci) -2 Core Courses\tDSC 5241 Natural Language Processing (3,0)\tNabeela Kausar -\t104\t06:30 PM - 09:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '13\tSocial Sciences\tBSSS\tBSSS 4 / BS Psychology 4\tSS 2418 Statistical Inferences\tDr. Syed Aziz Rasool\t203\t05:30 PM - 08:30 PM\tSZABIST University\n'
        'H-8/4 ISB Campus\n'
        '14\tMedia Sciences\tBS Media\tFilm & Television Production Major\tMD 4825 Screenwriting (3,0)\tDr. Naveed Ullah Hashmi\tMedia Lab\t02:20 PM - 05:20 PM\tSZABIST University\n'
        'H-8/4 ISB Campus'
    )

    items = parse_html_with_advanced_pandas(email_body)
    assert len(items) == 14

    by_row = {item['row_number']: item for item in items}

    assert by_row[1]['semester_display'] == 'BS (AF) 6 A'
    assert by_row[2]['semester_display'] == 'BS Media 4 A'
    assert by_row[3]['semester_display'] == 'BS Psychology 1'
    assert by_row[4]['semester_display'] == 'BS Psychology 3'
    assert by_row[5]['semester_display'] == 'BS Psychology 2'
    assert by_row[6]['semester_display'] == 'BS Psychology 2'
    assert by_row[7]['semester_display'] == 'BS Psychology 4'
    assert by_row[8]['semester_display'] == 'BS (AF) 4 A'
    assert by_row[9]['semester_display'] == 'MS Cyber Security - 1'
    assert by_row[10]['semester_display'] == 'MS Cyber Security - 2'
    assert by_row[11]['semester_display'] == 'MS Computer Science'
    assert by_row[12]['semester_display'] == 'MS(Data Sci) -2 Core Courses'
    assert by_row[13]['semester_display'] == 'BS Psychology 4'
    assert by_row[14]['semester_display'] == 'Film & Television Production Major'

    assert by_row[3]['course_title'] == 'Introduction to Social Sciences'
    assert by_row[4]['course_title'] == 'Mathematics and Statistics'
    assert by_row[5]['course_title'] == 'Philosphy'
    assert by_row[13]['course_title'] == 'Statistical Inferences'


def test_html_table_preserves_empty_faculty_column_without_shifting_fields():
    html = '''
    <table>
      <tr><th>Sr No</th><th>Department</th><th>Program</th><th>Section</th><th>Course</th><th>Faculty Name</th><th>Room</th><th>Class Time</th><th>Campus</th></tr>
      <tr><td>1</td><td>Computing</td><td>BSSE</td><td>BS(SE)-2A</td><td>CSC 1201 Programming (3,0)</td><td></td><td>201</td><td>08:00 AM - 09:30 AM</td><td>SZABIST University Campus</td></tr>
    </table>
    '''
    items = parse_html_with_advanced_pandas(html)
    assert len(items) == 1
    assert items[0]['faculty'] == 'TBD'
    assert items[0]['room'] == '201'
    assert items[0]['time'] == '08:00 AM - 09:30 AM'


def test_html_table_ignores_slot_headers_addresses_and_incomplete_rows():
    html = '''
    <table>
      <tr><th>Sr No</th><th>Department</th><th>Program</th><th>Section</th><th>Course</th><th>Faculty Name</th><th>Room</th><th>Class Time</th><th>Campus</th></tr>
      <tr><td colspan="9">SLOT 1 (08:00 AM - 11:00 AM)</td></tr>
      <tr><td>Address</td><td colspan="8">HMB Plaza, I-8 Markaz, Islamabad</td></tr>
      <tr><td>1</td><td>Computing</td><td>BSSE</td><td>BS(SE)-2A</td><td>CSC 1201 Programming (3,0)</td><td>Ayesha Khan</td><td>201</td><td>08:00 AM - 09:30 AM</td><td>SZABIST University Campus</td></tr>
      <tr><td>2</td><td>Computing</td><td>BSSE</td><td>BS(SE)-2B</td><td></td><td>Ayesha Khan</td><td>202</td><td></td><td>SZABIST University Campus</td></tr>
    </table>
    '''
    items = parse_html_with_advanced_pandas(html)
    assert len(items) == 1
    assert items[0]['course_title'] == 'Programming'


def test_parser_removes_exact_duplicate_classes():
    row = ('1\tComputer Sciences\tBSSE\tBS(SE)-2A\tCSC 1201 Programming (3,0)\t'
           'Ayesha Khan\t201\t08:00 AM - 09:30 AM\tSZABIST University Campus')
    items = parse_html_with_advanced_pandas(f'{row}\n{row.replace("1\\t", "2\\t", 1)}')
    assert len(items) == 1
