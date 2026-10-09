import requests
import json
import os
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
  },
  data=json.dumps({
    "model": "meta/muse-spark-1.3-contributor",
    "messages": [
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
  })
)
print(response.json())