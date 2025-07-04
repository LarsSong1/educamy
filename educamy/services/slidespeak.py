from dotenv import load_dotenv
import os

load_dotenv()
SLIDESPEAK_API_KEY = os.getenv("SLIDESPEAK_API_KEY")
url = "https://api.slidespeak.co/api/v1/presentation/generate"




headers = {
    "Content-Type": "application/json",
    "x-api-key": SLIDESPEAK_API_KEY
}