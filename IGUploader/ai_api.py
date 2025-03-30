import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

def generate_caption():
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": "Generate me a suggestive, creative and sexy caption. You are trying to attract a cute male. It must be short and consice. make use of emojis to convey emotion. ALWAYS format the output as a json object in the format. caption: followed by the generated caption. and only reply with the generated caption, no extra text"
                }
            ],
            temperature=0.9,
            response_format={ "type": "json_object" }
        )
        
        response_content = chat_completion.choices[0].message.content
        if response_content is  None:
            return "Error: Received empty repsonse from API"
        try:
            json_response = json.loads(response_content)
            return json_response.get("caption", "Default caption if none found")
        except json.JSONDecodeError:
            return f"Error: Invalid JSON response - {response_content}"
    except Exception as e:
        return f"Error: {str(e)}"

"""
Below is just kept for testing API.

This is not needed to run the main script.
"""


def main():
    caption = generate_caption()
    print(caption)

if __name__ == "__main__":
    main()
