import requests
import json

url = 'http://localhost:8862/api/show_project/FAERS_R1'
try:
    response = requests.get(url)
    data = response.json()
    print(f"Project: {data['projectName']}")
    print(f"First record counts: {data['records'][0]['counts']}")
    print(f"First record metadata keys: {data['records'][0]['meta'].keys()}")
except Exception as e:
    print(f"Error: {e}")
