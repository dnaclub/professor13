import requests

TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
WEBHOOK_URL = "https://professor1-6908.onrender.com/webhook"

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
response = requests.post(url, data={"url": WEBHOOK_URL})

print("Status:", response.status_code)
print("Response:", response.text)