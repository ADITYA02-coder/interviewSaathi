import io
import re
import zipfile

MAX_BYTES = 5 * 1024 * 1024


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if len(data) > MAX_BYTES:
        raise ValueError("File is larger than 5 MB.")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:8])
    elif name.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf8", "ignore")
        text = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", text)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf8", "ignore")
    else:
        raise ValueError("Upload a PDF, DOCX or TXT file.")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 30:
        raise ValueError("Could not read any text from this file. Is it a scanned image?")
    return text[:8000]
