import fitz, re
from docx import Document

def sectionize_texts(text):
    pattern = re.compile(r'(?=\b(\d+\.\d+ [A-Z][a-z]+(?: [A-Z][a-z]+)*|\d+ [A-Z\s]+)\b)')

    # Split the text using the pattern, capturing the matched section headers
    html_content = pattern.sub(lambda match: f"<h3>{match.group(1)}</h3>", text)

    return html_content

def clean_text(text):
    # Remove non-printable characters
    return ''.join(c for c in text if c.isprintable())
    
def extract_text_from_pdf(file_path):
    pages = ''
    with fitz.open(file_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf.load_page(page_num)
            text_data = ''

            # Extract text blocks
            blocks = page.get_text("blocks")  # Returns a list of tuples with block details

            for block in blocks:
                x0, y0, x1, y1, text, bn, block_type = block

                # Only process text blocks (skip images or other non-text blocks)
                if block_type == 0:  # 0 means text block in PyMuPDF
                    # text = re.sub(r'(?<=\b(\.)\b)\n', ' ', text).strip()
                    # text_data += '<p>'+clean_text(text)+'</p>'
                    text_data += '<p>'+text+'</p>'    
                    
            pages += text_data
    return [pages,]
    
def extract_text_from_docx(file_path, max_paragraphs_per_page=10):
    pages = ''
    doc = Document(file_path)
    text = ''
    paragraph_count = 0

    for para in doc.paragraphs:
        formatted_text=para.text.strip()
        if not formatted_text:
            continue
        # Add the paragraph to the text with a newline
        # text += '<p>'+clean_text(formatted_text)+'</p>' 
        text += '<p>'+formatted_text+'</p>' 
        paragraph_count += 1

        # Check if we have reached the max paragraphs per "page"
        if paragraph_count >= max_paragraphs_per_page:
            pages += text
            text = ''
            paragraph_count = 0

    # Add any remaining text as the last page
    if text:
        pages += text

    return [pages,]