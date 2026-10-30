import base64
import requests

with open("text.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

API_KEY = "API Key" ## API Key
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"

prompt_text = """You are a typography expert. Identify the font in this screenshot of text.
Respond with ONLY a JSON object, no markdown, with these keys:
"family" (best-match font family name, prefer well-known names),
"confidence" ("high" | "medium" | "low"),
"category" ("serif" | "sans-serif" | "monospace" | "script" | "display"),
"alternatives" (array of 2-3 similar font family names),
"sizeMinPx" (number), "sizeMaxPx" (number) - approximate rendered size of the main text in CSS px based on the image,
"sizeLabel" (e.g. "body text", "heading", "caption"),
"reasoning" (one or two sentences on the letterform features you used).
If there is no readable text, set family to "Unknown" and confidence to "low"."""

payload = {
    "contents": [{
        "parts": [
            {"text": prompt_text},
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": image_data
                }
            }
        ]
    }]
}

response = requests.post(url, json=payload)
print(response.json())