import fitz, re
from docx import Document
from charset_normalizer import from_path
import json

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

def generate_demographic_content(row, mode='RxLogix'):
    demographic_keys = [
            "Attachments Info-Link", "Age in Years", "Sex",
            "Weight In kg", "Medical History and Comments", "Reporter Qualifications", "Health Professional", "All Lab Tests",
            "Confirmatory Test Comments", "Seriousness", "All Outcomes"
    ]
        
    # Optional: Color cycle (or hardcode per key if needed)
    demographic_html = "<div class='mb-4 space-y-4 text-sm text-gray-800'>"

    for key in demographic_keys:
        value = str(row.get(key, "")).strip()
        if not value:
            continue

        if key in ["Medical History and Comments","Medical History/Medical History Comments"]:
            # Parse and render as bullet list
            items = [item.strip(' ;)') for item in value.split(';') if item.strip()]
            formatted = f"<p class='text-gray-900 mt-1'>{'; '.join(items)}</p>"
        else:
            # Regular paragraph value
            formatted = f"<p class='text-gray-900 mt-1'>{value}</p>"

        demographic_html += f"""
            <div>
            <h4>{key}</h4>
            {formatted}
            </div>
        """


    demographic_html += "</div>"
    return demographic_html
    
def generate_outcomes_content(row, mode='RxLogix'):
    # === Build meta.outcomes ===
    if mode == 'InfoVIP':
        categories = ['All LLTs', 'All PTs', 'All HLTs', 'All HLGTs', 'All SOCs']
        
        def parse_list(text):
            return [item.strip() for item in text.split(':') if item.strip()]
        
        include_start_date = False
    else:  # RxLogix mode
        categories = ['All SOCs', 'All HLGTs', 'All HLTs', 'All PTs', 'All LLTs']
        
        def parse_list(text):
            items = []
            for item in str(text).split(';'):
                item = item.strip()
                if not item:
                    continue
                # Try to extract "N) Term Name"
                match = re.match(r'^(\d+)\)\s*(.*)$', item)
                if match:
                    items.append((int(match.group(1)), match.group(2).strip()))
                else:
                    # Fallback for unnumbered items
                    items.append((0, item))
            return items
        
        include_start_date = True

    parsed_data = {category: parse_list(row.get(category, '')) for category in categories}
    max_items = max(len(parsed_data[category]) for category in categories)

    pt_table_html = [
        "<div class='mb-4 overflow-hidden'>",
        "<table class='min-w-full text-sm border border-gray-300 rounded shadow-md'>",
        "<thead class='bg-gray-100 text-left'><tr>",
        "<th class='px-4 py-2 border'>Term ID</th>",
        "<th class='px-4 py-2 border'>MedDRA</th>"
        "<th class='px-4 py-2 border'>PT</th>",
        "<th class='px-4 py-2 border'>LLT</th>",
    ]
    
    if include_start_date:
        pt_table_html.append("<th class='px-4 py-2 border'>Start Date</th>")
    
    pt_table_html.append("</tr></thead><tbody>")

    for i in range(max_items):
        if mode == 'InfoVIP':
            soc = parsed_data['All SOCs'][i] if i < len(parsed_data['All SOCs']) else ''
            hlgt = parsed_data['All HLGTs'][i] if i < len(parsed_data['All HLGTs']) else ''
            hlt = parsed_data['All HLTs'][i] if i < len(parsed_data['All HLTs']) else ''
            pt = parsed_data['All PTs'][i] if i < len(parsed_data['All PTs']) else ''
            llt = parsed_data['All LLTs'][i] if i < len(parsed_data['All LLTs']) else ''
            term_id = i + 1
        else:  # RxLogix mode
            soc = next((item[1] for item in parsed_data['All SOCs'] if item[0] == i+1), '')
            hlgt = next((item[1] for item in parsed_data['All HLGTs'] if item[0] == i+1), '')
            hlt = next((item[1] for item in parsed_data['All HLTs'] if item[0] == i+1), '')
            pt = next((item[1] for item in parsed_data['All PTs'] if item[0] == i+1), '')
            llt = next((item[1] for item in parsed_data['All LLTs'] if item[0] == i+1), '')
            term_id = i + 1
            term = row.get(f"PT Term Event {term_id}", "").strip()
            date = row.get(f"Start Date Event {term_id}", "").strip()

        if any([soc, hlgt, hlt, pt, llt]):
            row_html = [
                f"<tr class='hover:bg-gray-50'>",
                f"<td class='px-4 py-2 border'>{term_id}</td>",
                f"<td class='px-4 py-2 border'>{soc}/{hlgt}/{hlt}</td>",
                f"<td class='px-4 py-2 border'>{pt or term if mode == 'RxLogix' else pt}</td>",
                f"<td class='px-4 py-2 border'>{llt}</td>",
            ]
            
            if include_start_date:
                row_html.append(f"<td class='px-4 py-2 border'>{date}</td>")
            
            row_html.append("</tr>")
            pt_table_html.extend(row_html)

    pt_table_html.append("</tbody></table></div>")
    return "\n".join(pt_table_html)


def generate_products_content(row, columns, mode='RxLogix'):
    # === Build meta.products grouped by Role ===
    if mode == 'RxLogix':
        product_keys = [
            "Product Name", "Product Active Ingredient", "Reported Verbatim", "Compounded Product", "Combination Product",
            "Role", "Reason for Use", "Strength", "Strength (Unit)", "Dose (Amount)", "Dose (Unit)",
            "Dosage Text", "Dosage Form", "Route", "Frequency", "Dechallenge", "Rechallenge",
            "Start Date", "Stop Date", "Therapy Duration (Days)", "Therapy Duration (Verbatim)", "Time To Onset (Days)", "Manufacturer",
            "Application Type", "Application #", "NDC #", "LOT #"
        ]
    else:  # InfoVIP export mode
        product_keys = [
            "Product Name", "Prod Active Ingred", "Reported Verbatim", "Compounded Product", "Combination Product",
            "Role", "Reason for Use", "Strength", "Strength Unit", "Dose Amount", "Dose Unit",
            "Dosage Text", "Dosage Form", "Route", "Frequency", "Dechallenge", "Rechallenge",
            "Start Date", "Stop Date", "Therapy Duration", "Time To Onset", "Manufacturer",
            "Application Type", "Application Number", "NDC Number", "Lot Number"
        ]

    # Detect prefixes (Product 1, Product 2, etc.)
    product_prefixes = set()
    for col in columns:
        col_str = str(col)
        if col_str.startswith("Product ") and "Product Name" in col_str:
            prefix = col_str.split("Product Name")[0].strip()
            product_prefixes.add(prefix)

    # Categorize products by Role
    grouped_products = {"Suspect": [], "Concomitant":[], "Other": []}

    sorted_prefixes = sorted(product_prefixes, key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 0)
    for prefix in sorted_prefixes:
        product_data = {str(col)[len(prefix):].strip(): row[col] for col in columns if str(col).startswith(prefix)}
        role = str(product_data.get("Role", "")).strip().lower()
        if role == "suspect":
            grouped_products["Suspect"].append(product_data)
        elif role == "concomitant":
            grouped_products["Concomitant"].append(product_data)
        else:
            grouped_products["Other"].append(product_data)

    # Build product entry as mini-table
    def render_product(product_data):
        rows = ""
        for key in product_keys:
            value = str(product_data.get(key, "")).strip()
            if value:
                rows += f"""
                <tr>
                <td class='pr-4 font-medium text-gray-700'>{key}:</td>
                <td class='text-gray-900'>{value}</td>
                </tr>
                """
        return f"""
            <div class='mb-4 border border-gray-200 rounded-lg bg-white p-3 shadow-sm'>
            <h4 class='font-semibold text-blue-800 mb-2'>{product_data.get("Product Name", "(Unnamed Product)")}</h4>
            <table class='text-sm table-auto'>
                <tbody>
                {rows}
                </tbody>
            </table>
            </div>
            """

    # Final HTML output
    products_html = ""

    for category, items in grouped_products.items():
        if not items:
            continue

        block = "\n".join(render_product(p) for p in items)

        products_html += f"""
        <details class='mb-4 border rounded-lg bg-white shadow-sm overflow-hidden'>
        <summary class='cursor-pointer select-none px-4 py-2 font-semibold bg-blue-50 text-blue-800 hover:bg-blue-100'>
                    {category} Products ({len(items)})
        </summary>
        <div class='px-4 py-3'>
            {block}
        </div>
        </details>
        """
    return products_html

def load_json_with_charset_normalizer(file_path):
    """
    Load a JSON file using charset-normalizer to auto-detect encoding.
    Returns parsed JSON content.
    """
    # Auto-detect and decode content
    result = from_path(file_path)
    decoded = result.best()
    
    if decoded is None:
        raise ValueError(f"Unable to detect encoding for file: {file_path}")

    return json.loads(str(decoded))


