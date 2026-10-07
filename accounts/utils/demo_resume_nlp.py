from pathlib import Path

from .resume_parser import extract_resume_text
from .resume_nlp import parse_resume_data


# ---------------------------------
# Find resume automatically
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent

pdf_files = list(BASE_DIR.glob("*.pdf"))
docx_files = list(BASE_DIR.glob("*.docx"))


# ---------------------------------
# Select a resume
# ---------------------------------

resume_file = None
file_type = None

if pdf_files:
    resume_file = pdf_files[0]
    file_type = "pdf"

elif docx_files:
    resume_file = docx_files[0]
    file_type = "docx"


if not resume_file:

    print("No PDF or DOCX resume found.")

    exit()


print("\n==============================")
print("Testing Resume:", resume_file.name)
print("File Type:", file_type)
print("==============================")


# ---------------------------------
# Extract resume text
# ---------------------------------

with open(resume_file, "rb") as file:

    raw_text, cleaned_text = extract_resume_text(
        file,
        file_type,
    )


# ---------------------------------
# Parse resume
# ---------------------------------

result = parse_resume_data(
    cleaned_text
)


# ---------------------------------
# Display result
# ---------------------------------

print(
    "\n========== STRUCTURED RESUME DATA ==========\n"
)

print(result)