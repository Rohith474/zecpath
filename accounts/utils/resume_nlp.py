import re

from django.utils import timezone

# ============================================================

# PREDEFINED SKILL LIBRARY

# ============================================================



SKILL_LIBRARY = [

    "Python",

    "Java",

    "C++",

    "C",

    "JavaScript",

    "PHP",

    "SQL",

    "Django",

    "Flask",

    "REST API",

    "HTML",

    "CSS",

    "React",

    "Node.js",

    "Machine Learning",

    "Data Science",

    "TensorFlow",

    "PyTorch",

    "PostgreSQL",

    "MySQL",

    "MongoDB",

    "Git",

    "GitHub",

    "Docker",

    "AWS",

    "Azure",

    "Arduino",

    "MATLAB",

    "AutoCAD",

    "ANSYS",

    "Razorpay",

    "Android Studio",

    "VS Code",

]





# ============================================================

# SECTION NAMES

# ============================================================



SECTION_NAMES = {

    "experience": [

        "experience",

        "work experience",

        "professional experience",

        "employment history",

        "work history",

    ],



    "education": [

        "education",

        "academic background",

        "educational background",

    ],



    "skills": [

        "skills",

        "technical skills",

        "technical skills / coursework",

        "coursework / skills",

        "skills & technologies",

        "technologies",

    ],



    "projects": [

        "projects",

        "academic projects",

        "personal projects",

        "key projects",

        "project experience",

    ],



    "certifications": [

        "certifications",

        "certificates",

        "professional certifications",

    ],



    "languages": [

        "languages",

    ],



    "extracurricular": [

        "extracurricular",

        "extracurricular activities",

        "activities",

    ],

}





# ============================================================

# COMMON PATTERNS

# ============================================================



BULLET_PATTERN = re.compile(

    r"^[•●▪◦‣*-]\s*"

)



DATE_RANGE_PATTERN = re.compile(

    r"\b"

    r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)"

    r"[A-Z]*"

    r"\s+\d{4}"

    r"\s*(?:–|-|—|TO)\s*"

    r"(?:"

    r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)"

    r"[A-Z]*\s+\d{4}"

    r"|"

    r"PRESENT"

    r")"

    r"\b",

    re.IGNORECASE,

)



YEAR_RANGE_PATTERN = re.compile(

    r"\b(19|20)\d{2}\s*(?:–|-|—|to)\s*(?:\d{4}|present)\b",

    re.IGNORECASE,

)



YEAR_PATTERN = re.compile(

    r"\b(?:19|20)\d{2}\b"

)





# ============================================================

# TEXT NORMALIZATION

# ============================================================



def normalize_text(text):

    """

    Normalize extracted resume text into useful lines.



    Important:

    We preserve bullet characters because they help us

    distinguish descriptions from headings/titles.

    """



    text = text.replace("\r\n", "\n")

    text = text.replace("\r", "\n")



    # Replace common PDF artifacts.

    text = text.replace("\u00a0", " ")



    lines = []



    for raw_line in text.splitlines():



        line = raw_line.strip()



        if not line:

            continue



        # Remove excessive spaces.

        line = re.sub(r"[ \t]+", " ", line)



        lines.append(line)



    return lines





# ============================================================

# SECTION DETECTION

# ============================================================



def split_into_sections(lines):



    sections = {

        "header": []

    }



    current_section = "header"



    for line in lines:



        normalized = line.lower().strip()



        # Remove common punctuation from section headings.

        normalized = re.sub(

            r"[:\-]+$",

            "",

            normalized,

        ).strip()



        found_section = None



        for section, names in SECTION_NAMES.items():



            if normalized in names:

                found_section = section

                break



        if found_section:



            current_section = found_section



            if current_section not in sections:

                sections[current_section] = []



        else:



            sections.setdefault(

                current_section,

                [],

            )



            sections[current_section].append(line)



    return sections





# ============================================================

# HELPER FUNCTIONS

# ============================================================



def remove_bullet(line):

    """

    Remove bullet marker without destroying the actual text.

    """



    return re.sub(

        r"^[•●▪◦‣*-]\s*",

        "",

        line.strip(),

    ).strip()





def is_bullet(line):



    return bool(

        BULLET_PATTERN.match(

            line.strip()

        )

    )





def contains_date_range(line):



    return bool(

        DATE_RANGE_PATTERN.search(line)

        or YEAR_RANGE_PATTERN.search(line)

    )





def extract_date_range(line):



    match = DATE_RANGE_PATTERN.search(line)



    if match:

        return match.group(0).strip()



    match = YEAR_RANGE_PATTERN.search(line)



    if match:

        return match.group(0).strip()



    return None





def clean_date_from_line(line):



    line = DATE_RANGE_PATTERN.sub(

        "",

        line,

    )



    line = YEAR_RANGE_PATTERN.sub(

        "",

        line,

    )



    return re.sub(

        r"\s{2,}",

        " ",

        line,

    ).strip(" -–—,|")





def looks_like_contact(line):



    lower = line.lower()



    if "@" in line:

        return True



    if "linkedin" in lower:

        return True



    if "github.com" in lower:

        return True



    if re.search(

        r"\+?\d[\d\s()-]{8,}",

        line,

    ):

        return True



    return False





# ============================================================

# SKILL EXTRACTION

# ============================================================



def extract_skills(text):



    found_skills = []



    text_lower = text.lower()



    # Sort longest first so C++ is checked before C.

    skills_sorted = sorted(

        SKILL_LIBRARY,

        key=len,

        reverse=True,

    )



    for skill in skills_sorted:



        pattern = re.escape(

            skill.lower()

        )



        # More flexible matching than \b because

        # technologies such as C++, Node.js etc.

        # don't behave well with word boundaries.



        if re.search(

            r"(?<![a-z0-9+#])"

            + pattern

            + r"(?![a-z0-9+#])",

            text_lower,

        ):



            if skill not in found_skills:

                found_skills.append(skill)



    return found_skills



# ============================================================

# ROLE EXTRACTION

# ============================================================



def extract_role(header_lines):



    if not header_lines:

        return None



    # --------------------------------------------------------

    # Job-title keywords.

    # We only accept a header line as a role when it contains

    # a clear professional/job-title keyword.

    # --------------------------------------------------------



    role_keywords = [

        "engineer",

        "developer",

        "designer",

        "manager",

        "analyst",

        "consultant",

        "architect",

        "administrator",

        "specialist",

        "scientist",

        "intern",

        "trainee",

        "programmer",

        "technician",

        "accountant",

        "recruiter",

        "researcher",

        "student",

        "founder",

        "director",

        "executive",

        "officer",

        "lead",

        "associate",

        "assistant",

    ]



    # --------------------------------------------------------

    # Ignore lines that are clearly contact/location data.

    # --------------------------------------------------------



    for line in header_lines:



        candidate = line.strip()



        if not candidate:

            continue



        lower = candidate.lower()



        # Skip email/contact information.

        if "@" in candidate:

            continue



        if "linkedin" in lower:

            continue



        if "github" in lower:

            continue



        # Skip phone numbers.

        if re.search(

            r"\+?\d[\d\s().-]{8,}",

            candidate,

        ):

            continue



        # Skip obvious location lines.

        location_words = [

            "kerala",

            "india",

            "mumbai",

            "delhi",

            "chennai",

            "bangalore",

            "bengaluru",

            "hyderabad",

            "thrissur",

            "kochi",

            "amaravati",

            "tamil nadu",

            "andhra pradesh",

            "karnataka",

            "maharashtra",

        ]



        if any(

            word in lower

            for word in location_words

        ):

            continue



        # ----------------------------------------------------

        # Skip common resume section headings.

        # ----------------------------------------------------



        forbidden = {

            "summary",

            "profile",

            "objective",

            "education",

            "experience",

            "work experience",

            "professional experience",

            "skills",

            "technical skills",

            "projects",

            "certifications",

            "languages",

            "extracurricular",

            "activities",

        }



        if lower in forbidden:

            continue



        # ----------------------------------------------------

        # A role must contain a recognized job-title keyword.

        # ----------------------------------------------------



        if any(

            re.search(

                r"\b" + re.escape(keyword) + r"\b",

                lower,

            )

            for keyword in role_keywords

        ):



            # Avoid long sentences being treated as roles.

            if len(candidate.split()) <= 8:



                # Avoid bullet/description sentences.

                if not candidate.endswith("."):



                    return candidate



    # --------------------------------------------------------

    # No valid role was explicitly found in the header.

    # --------------------------------------------------------



    return None



# ============================================================

# EXPERIENCE PARSING

# ============================================================



def extract_experience(lines):

    """

    Extract experience positions from resume text.



    Supports formats such as:



    • ABC Technologies(Python Developer) – JAN 2023 - JAN 2026



    • ABC Technologies (Python Developer)

      JAN 2023 - JAN 2026



    ABC Technologies JAN 2023 - JAN 2026

    Python Developer



    Python Developer JAN 2023 - JAN 2026

    ABC Technologies

    """



    positions = []



    i = 0



    while i < len(lines):



        original_line = lines[i].strip()



        if not original_line:

            i += 1

            continue



        # Remove bullet before processing.

        line = remove_bullet(original_line)



        # ----------------------------------------------------

        # Find a line containing an experience date range

        # ----------------------------------------------------



        if not contains_date_range(line):

            i += 1

            continue



        duration = extract_date_range(line)



        if not duration:

            i += 1

            continue



        # Remove the date from the line.

        remaining_text = clean_date_from_line(line)



        company = ""

        title = ""



        # ----------------------------------------------------

        # CASE 1


        # ABC Technologies(Python Developer)

        # JAN 2023 - JAN 2026


        # OR


        # ABC Technologies (Python Developer)

        # – JAN 2023 - JAN 2026


        # Extract:

        # company = ABC Technologies

        # title = Python Developer

        # ----------------------------------------------------



        parenthesis_match = re.match(

            r"^(.*?)\s*\((.*?)\)\s*$",

            remaining_text,

        )



        if parenthesis_match:



            company = parenthesis_match.group(1).strip()



            title = parenthesis_match.group(2).strip()



            i += 1



        # ----------------------------------------------------

        # CASE 2


        # Company Name - Python Developer

        # JAN 2023 - JAN 2026

        # ----------------------------------------------------



        elif " - " in remaining_text:



            parts = remaining_text.split(

                " - ",

                1,

            )



            company = parts[0].strip()



            title = parts[1].strip()



            i += 1



        # ----------------------------------------------------

        # CASE 3


        # COMPANY + DATE

        # TITLE

        # ----------------------------------------------------



        else:



            company = remaining_text.strip()



            # Check next line for title.

            if i + 1 < len(lines):



                next_line = lines[i + 1].strip()



                # Do not use another experience entry

                # as the title.

                if (

                    next_line

                    and not is_bullet(next_line)

                    and not contains_date_range(next_line)

                ):



                    title = remove_bullet(

                        next_line

                    )



                    i += 2



                else:



                    # If there is no separate title,

                    # keep the company and use a generic title.

                    title = "Not specified"



                    i += 1



            else:



                title = "Not specified"



                i += 1



        # ----------------------------------------------------

        # Clean values

        # ----------------------------------------------------



        company = remove_bullet(company)



        title = remove_bullet(title)



        # ----------------------------------------------------

        # Skip invalid entries

        # ----------------------------------------------------



        if not company:

            continue



        if len(company.split()) > 20:

            continue



        # ----------------------------------------------------

        # Create position

        # ----------------------------------------------------



        position = {

            "company": company,

            "title": title,

            "duration": duration,

            "description": [],

        }



        # ----------------------------------------------------

        # Collect description lines until:


        # 1. Another experience entry with a date

        # 2. Another resume section

        # ----------------------------------------------------



        while i < len(lines):



            next_line = lines[i].strip()



            if not next_line:

                i += 1

                continue



            # New experience entry.

            if contains_date_range(next_line):

                break



            normalized_next = re.sub(

                r"[:\-]+$",

                "",

                next_line.lower().strip(),

            )



            # Stop at another section.

            if normalized_next in {

                name.lower()

                for names in SECTION_NAMES.values()

                for name in names

            }:

                break



            # Bullet description.

            if is_bullet(next_line):



                description = remove_bullet(

                    next_line

                )



                if description:

                    position[

                        "description"

                    ].append(

                        description

                    )



            else:



                # Wrapped continuation line.

                if position["description"]:



                    position[

                        "description"

                    ][-1] += (

                        " " + next_line

                    )



            i += 1



        positions.append(

            position

        )



    return positions

# ============================================================

# EXPERIENCE TOTAL YEARS

# ============================================================

def calculate_total_experience(positions):

    """

    Calculate total experience in years from

    extracted experience positions.



    Supports:

    JAN 2023 - JAN 2026

    JAN 2023 – JAN 2026

    OCT 2024 - PRESENT

    2021 - 2023

    2023 - PRESENT

    """



    if not positions:

        return None



    total_months = 0



    month_mapping = {

        "JAN": 1,

        "FEB": 2,

        "MAR": 3,

        "APR": 4,

        "MAY": 5,

        "JUN": 6,

        "JUL": 7,

        "AUG": 8,

        "SEP": 9,

        "SEPT": 9,

        "OCT": 10,

        "NOV": 11,

        "DEC": 12,

    }



    current_date = timezone.localdate()



    for position in positions:



        duration = position.get("duration")



        if not duration:

            continue



        duration = (

            duration.upper()

            .replace("–", "-")

            .replace("—", "-")

            .strip()

        )



        # ====================================================

        # MONTH YEAR - MONTH YEAR


        # Example:

        # JAN 2023 - JAN 2026

        # OCT 2024 - PRESENT

        # ====================================================



        month_year_match = re.search(

            r"([A-Z]+)\s+(\d{4})"

            r"\s*(?:-|TO)\s*"

            r"(?:(?:([A-Z]+)\s+(\d{4}))|PRESENT)",

            duration,

        )



        if month_year_match:



            start_month_name = (

                month_year_match.group(1)

            )



            start_year = int(

                month_year_match.group(2)

            )



            end_month_name = (

                month_year_match.group(3)

            )



            end_year_value = (

                month_year_match.group(4)

            )



            # ----------------------------------------

            # Start month

            # ----------------------------------------



            start_month = month_mapping.get(

                start_month_name

            )



            if start_month is None:

                continue



            # ----------------------------------------

            # End date

            # ----------------------------------------



            if "PRESENT" in duration:



                end_month = current_date.month

                end_year = current_date.year



            else:



                end_month = month_mapping.get(

                    end_month_name

                )



                if end_month is None:

                    continue



                end_year = int(

                    end_year_value

                )



            # ----------------------------------------

            # Calculate months

            # ----------------------------------------



            months = (

                (end_year - start_year) * 12

                + (end_month - start_month)

            )



            if months > 0:

                total_months += months



            continue



        # ====================================================

        # YEAR - YEAR


        # Example:

        # 2021 - 2023

        # 2023 - PRESENT

        # ====================================================



        year_match = re.search(

            r"\b((?:19|20)\d{2})\s*"

            r"(?:-|TO)\s*"

            r"((?:19|20)\d{2}|PRESENT)",

            duration,

        )



        if year_match:



            start_year = int(

                year_match.group(1)

            )



            end_value = (

                year_match.group(2)

            )



            if end_value == "PRESENT":



                end_year = current_date.year



            else:



                end_year = int(

                    end_value

                )



            months = (

                end_year - start_year

            ) * 12



            if months > 0:

                total_months += months



    # ========================================================

    # No valid experience duration found

    # ========================================================



    if total_months == 0:

        return None



    total_years = (

        total_months / 12

    )



    return round(

        total_years,

        2,

    )



# ============================================================

# EDUCATION PARSING

# ============================================================



def detect_education_level(text):



    lower = text.lower()



    if re.search(

        r"\b(ph\.?d|phd|doctorate|doctoral)\b",

        lower,

    ):

        return "PhD"



    if re.search(

        r"\b(m\.?tech|m\.?e\.?|m\.?sc|mba|master)\b",

        lower,

    ):

        return "Postgraduate"



    if re.search(

        r"\b(b\.?tech|b\.?e\.?|b\.?sc|bca|bba|bachelor)\b",

        lower,

    ):

        return "Undergraduate"



    if re.search(

        r"\b(class\s*12|12th|intermediate|higher secondary|plus\s*two)\b",

        lower,

    ):

        return "Class 12"



    if re.search(

        r"\b(class\s*10|10th|high school|highschool|secondary)\b",

        lower,

    ):

        return "Class 10"



    return None





def extract_gpa(line):



    match = re.search(

        r"(?:CGPA|GPA)\s*[:\-]?\s*"

        r"([\d.]+(?:\s*/\s*[\d.]+)?)",

        line,

        re.IGNORECASE,

    )



    if match:

        return match.group(1).strip()



    return None





def extract_percentage(line):



    match = re.search(

        r"(\d+(?:\.\d+)?)\s*%",

        line,

    )



    if match:

        return match.group(1) + "%"



    return None





def extract_year_information(line):



    matches = YEAR_PATTERN.findall(line)



    if not matches:

        return None



    if len(matches) >= 2:



        return (

            f"{matches[0]} - {matches[1]}"

        )



    return matches[0]





def extract_education(lines):



    education = []



    i = 0



    while i < len(lines):



        line = lines[i].strip()



        level = detect_education_level(

            line

        )



        # ----------------------------------------------------

        # CASE 1:


        # Everything on one line.


        # 2023 – 2026 BSc Computer Science,

        # College of Applied Sciences Nattika

        # (GPA: 6.5/10.0)

        # ----------------------------------------------------



        if level:



            combined = line



            # Sometimes the next line contains the

            # continuation of the qualification.

            if (

                i + 1 < len(lines)

                and not detect_education_level(

                    lines[i + 1]

                )

                and not lines[i + 1].lower()

                in {

                    "projects",

                    "experience",

                    "skills",

                    "certifications",

                }

            ):



                next_line = lines[i + 1]



                # Only join if it doesn't look like

                # a completely separate section.

                if (

                    not is_bullet(next_line)

                    and not contains_date_range(

                        next_line

                    )

                ):

                    combined += " " + next_line








            year = extract_year_information(

                combined

            )



            gpa = extract_gpa(

                combined

            )



            percentage = extract_percentage(

                combined

            )



            # ------------------------------------------------

            # Extract qualification name.

            # ------------------------------------------------



            qualification = combined



            qualification = re.sub(

                r"\b(?:19|20)\d{2}\s*(?:–|-|—)\s*(?:19|20)?\d{2}\b",

                "",

                qualification,

            )



            qualification = re.sub(

                r"\b(?:19|20)\d{2}\b",

                "",

                qualification,

            )



            qualification = re.sub(

                r"\(\s*(?:CGPA|GPA)\s*[:\-]?\s*[\d.]+(?:\s*/\s*[\d.]+)?\s*\)",

                "",

                qualification,

                flags=re.IGNORECASE,

            )



            qualification = re.sub(

                r"(?:CGPA|GPA)\s*[-:]?\s*[\d.]+(?:\s*/\s*[\d.]+)?",

                "",

                qualification,

                flags=re.IGNORECASE,

            )



            qualification = re.sub(

                r"\s{2,}",

                " ",

                qualification,

            ).strip(" ,-")



            # ------------------------------------------------

            # Extract institution.


            # Usually appears after a comma.

            # ------------------------------------------------



            institution = None



            if "," in qualification:



                parts = [

                    part.strip()

                    for part in qualification.split(

                        ","

                    )

                    if part.strip()

                ]



                if len(parts) >= 2:



                    qualification = parts[0]



                    institution = ", ".join(

                        parts[1:]

                    )



            # ------------------------------------------------

            # For Class 10 / Class 12, don't call the

            # qualification a "degree".

            # ------------------------------------------------



            item = {

                "level": level,

                "qualification": qualification,

                "institution": institution,

                "year": year,

            }



            if gpa:

                item["gpa"] = gpa



            if percentage:

                item["percentage"] = percentage



            education.append(item)



        i += 1



    return education





# ============================================================

# PROJECT PARSING

# ============================================================



def looks_like_project_title(line):



    clean = remove_bullet(line)



    if not clean:

        return False



    if looks_like_contact(clean):

        return False



    # A project title normally isn't a complete sentence.

    if clean.endswith("."):

        return False



    # A project title usually has reasonable length.

    if len(clean.split()) > 15:

        return False



    return True





def extract_projects(lines):



    projects = []



    current_project = None



    for line in lines:



        stripped = line.strip()



        if not stripped:

            continue



        bullet = is_bullet(

            stripped

        )



        clean_line = remove_bullet(

            stripped

        )



        # ----------------------------------------------------

        # Bullet = description

        # ----------------------------------------------------



        if bullet:



            if current_project:



                current_project[

                    "description"

                ].append(clean_line)



            continue



        # ----------------------------------------------------

        # Non-bullet:


        # If there is no current project, create one.

        # ----------------------------------------------------



        if current_project is None:



            if looks_like_project_title(

                clean_line

            ):



                current_project = {

                    "title": clean_line,

                    "description": [],

                }



            continue



        # ----------------------------------------------------

        # A non-bullet line after a description may be:


        # 1. Wrapped continuation

        # 2. A new project title


        # We only treat it as a new title if the

        # previous line was not a description continuation

        # and the line looks sufficiently title-like.

        # ----------------------------------------------------



        if current_project["description"]:



            # Most PDF extraction wrapping appears here.

            current_project[

                "description"

            ][-1] += " " + clean_line



        else:



            # No description yet, therefore this is

            # probably the next project.

            projects.append(

                current_project

            )



            current_project = {

                "title": clean_line,

                "description": [],

            }



    if current_project:



        projects.append(

            current_project

        )



    # --------------------------------------------------------

    # Remove obvious false positives.

    # --------------------------------------------------------



    cleaned_projects = []



    for project in projects:



        title = project["title"].strip()



        if looks_like_contact(title):

            continue



        if title.lower() in {

            "email",

            "phone",

            "linkedin",

            "github",

        }:

            continue



        cleaned_projects.append(

            project

        )



    return cleaned_projects





# ============================================================

# CERTIFICATION EXTRACTION

# ============================================================



def extract_certifications(lines):



    certifications = []



    for line in lines:



        clean_line = remove_bullet(

            line

        )



        if not clean_line:

            continue



        if clean_line.lower() in {

            "certifications",

            "certificates",

        }:

            continue



        certifications.append(

            clean_line

        )



    return certifications

# ---------------------------------

# Contact information extraction

# ---------------------------------



def extract_email(text):



    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"



    match = re.search(

        email_pattern,

        text,

        re.IGNORECASE,

    )



    if match:

        return match.group(0)



    return None





def extract_phone(text):



    phone_pattern = r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}(?!\d)"



    matches = re.findall(

        phone_pattern,

        text,

    )



    for phone in matches:



        digits = re.sub(

            r"\D",

            "",

            phone,

        )



        # Indian mobile number validation

        if len(digits) >= 10:



            return phone.strip()



    return None



# ============================================================

# MAIN PARSER

# ============================================================



def parse_resume_data(text):



    lines = normalize_text(

        text

    )



    sections = split_into_sections(

        lines

    )



    # --------------------------------------------------------

    # Skills

    # --------------------------------------------------------



    skills_text = "\n".join(

        sections.get(

            "skills",

            [],

        )

    )



    all_text = "\n".join(

        lines

    )



    skills = extract_skills(

        skills_text + "\n" + all_text

    )



    # --------------------------------------------------------

    # Experience

    # --------------------------------------------------------



    experience_positions = (

        extract_experience(

            sections.get(

                "experience",

                [],

            )

        )

    )



    total_years = (

        calculate_total_experience(

            experience_positions

        )

    )



    # --------------------------------------------------------

    # Education

    # --------------------------------------------------------



    education = extract_education(

        sections.get(

            "education",

            [],

        )

    )



    # --------------------------------------------------------

    # Projects

    # --------------------------------------------------------



    projects = extract_projects(

        sections.get(

            "projects",

            [],

        )

    )



    # --------------------------------------------------------

    # Certifications

    # --------------------------------------------------------



    certifications = (

        extract_certifications(

            sections.get(

                "certifications",

                [],

            )

        )

    )



    # --------------------------------------------------------

    # Final structured response

    # --------------------------------------------------------



    return {

        "role": extract_role(

            sections.get(

                "header",

                [],

            )

        ),

        "email": extract_email(all_text),



        "phone": extract_phone(all_text),

        "skills": skills,



        "experience": {

            "total_years": total_years,

            "positions": experience_positions,

        },



        "education": education,



        "projects": projects,



        "certifications": certifications,

    }