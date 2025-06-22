from dotenv import load_dotenv
import os

load_dotenv()

print(f"GENAI_API_KEY: {os.getenv('GEMINI_API_KEY')}")
