import requests
import json

url = "http://localhost:11434/api/generate"
data = {
    "model": "llama3.2",
    "prompt": "Hello, just testing the API.",
     "stream": True  # Enable streaming mode
}


response = requests.post(url, json=data, stream=True)

filtered_text = ""

# Read the response line by line
for line in response.iter_lines():
    if line:
        try:
            json_data = json.loads(line.decode("utf-8"))
            filtered_text += json_data.get("response", "")
        except json.JSONDecodeError as e:
            print("JSON Decode Error:", e)

print("\nFiltered Output:\n", filtered_text)
