import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
with open("test.txt", "w") as f:
    f.write("Hello world!")
try:
    file = genai.upload_file("test.txt", mime_type="text/plain")
    print(f"Uploaded successfully! URI: {file.uri}")
except Exception as e:
    import traceback
    traceback.print_exc()
