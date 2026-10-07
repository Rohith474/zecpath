import re

import pdfplumber
from docx import Document


def extract_text_from_pdf(file):
    """
    Extract text from a PDF resume.
    """

    text = []

    with pdfplumber.open(file) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text.append(page_text)

    return "\n".join(text)


def extract_text_from_docx(file):
    """
    Extract text from a DOCX resume.
    """

    document = Document(file)

    text = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n".join(text)


def clean_resume_text(text):
    """
    Clean and normalize extracted resume text.
    """

    # Replace multiple spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at the beginning/end of lines
    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    # Remove empty lines at beginning/end
    text = "\n".join(lines).strip()

    return text


def extract_resume_text(file, file_type):
    """
    Extract and clean resume text based on file type.
    """

    if file_type == "pdf":

        raw_text = extract_text_from_pdf(file)

    elif file_type == "docx":

        raw_text = extract_text_from_docx(file)

    else:

        raise ValueError(
            "Unsupported file type."
        )

    cleaned_text = clean_resume_text(
        raw_text
    )

    return raw_text, cleaned_text