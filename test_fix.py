import sys
import os

# Add the scripts directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'development', 'scripts'))

from data_loader import load_data_from_db

try:
    data = load_data_from_db('server/database/llm4ae.db')
    print(f"Loaded {len(data)} items")
    if data:
        for i in range(min(5, len(data))):
            page_content = data[i]['pages'][0]
            num_anns = len(data[i]['annotations'])
            print(f"Sample {i}: pages[0] type={type(page_content)}, length={len(page_content) if page_content else 'None'}, annotations={num_anns}")
            if page_content:
                print(f"  Snippet: {page_content[:100]}...")
            else:
                print(f"  WARNING: Page content is empty or None!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
