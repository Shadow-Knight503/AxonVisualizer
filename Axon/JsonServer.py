import json
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/data")
def get_local_json():
    # Open and load the local JSON file
    with open('network_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    # FastAPI automatically converts dictionaries into JSON responses
    return data
