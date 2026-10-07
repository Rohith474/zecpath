from pathlib import Path

from .resume_parser import extract_resume_text


# ---------------------------------
# Find files automatically
# ---------------------------------

BASE_DIR = Path(__file__).resolve().parent


pdf_files = list(BASE_DIR.glob("*.pdf"))
docx_files = list(BASE_DIR.glob("*.docx"))


# ---------------------------------
# Test PDF
# ---------------------------------

if pdf_files:

    pdf_file = pdf_files[0]

    print("\n==============================")
    print("Testing PDF:", pdf_file.name)
    print("==============================")

    with open(pdf_file, "rb") as file:

        raw_text, cleaned_text = extract_resume_text(
            file,
            "pdf",
        )

    print("\n========== PDF RAW TEXT ==========\n")
    print(raw_text)

    print("\n========== PDF CLEANED TEXT ==========\n")
    print(cleaned_text)

else:

    print("No PDF file found in utils folder.")


# ---------------------------------
# Test DOCX
# ---------------------------------

if docx_files:

    docx_file = docx_files[0]

    print("\n==============================")
    print("Testing DOCX:", docx_file.name)
    print("==============================")

    with open(docx_file, "rb") as file:

        raw_text, cleaned_text = extract_resume_text(
            file,
            "docx",
        )

    print("\n========== DOCX RAW TEXT ==========\n")
    print(raw_text)

    print("\n========== DOCX CLEANED TEXT ==========\n")
    print(cleaned_text)

else:

    print("No DOCX file found in utils folder.")