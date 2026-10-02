import pytest
import zipfile
from io import BytesIO

from lib.career import validate_resume_upload


class FakeFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self.data = data


def test_valid_pdf_passes_validation():
    file = FakeFile("resume.pdf", "application/pdf", b"%PDF-1.4\n% dummy pdf")

    assert validate_resume_upload(file.data, file.filename, file.content_type) is None


def test_rejects_invalid_docx_file():
    file = FakeFile("resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"doc")

    with pytest.raises(ValueError, match="PDF"):
        validate_resume_upload(file.data, file.filename, file.content_type)


def test_accepts_valid_doc_and_docx():
    validate_resume_upload(bytes.fromhex("D0CF11E0A1B11AE1") + b"document", "resume.doc", "application/msword")
    data = BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    validate_resume_upload(data.getvalue(), "resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_rejects_mismatched_pdf_metadata():
    with pytest.raises(ValueError, match="valid PDF"):
        validate_resume_upload(b"%PDF-1.4\n", "resume.pdf", "text/plain")


def test_rejects_invalid_pdf_signature():
    with pytest.raises(ValueError, match="valid PDF"):
        validate_resume_upload(b"not a pdf", "resume.pdf", "application/pdf")


def test_rejects_files_over_5mb():
    file = FakeFile("resume.pdf", "application/pdf", b"a" * (5 * 1024 * 1024 + 1))

    with pytest.raises(ValueError, match="5 MB"):
        validate_resume_upload(file.data, file.filename, file.content_type)
