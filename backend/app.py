from flask import Flask, request, jsonify
import os
import subprocess
import whisper
# import openai
import json


app = Flask(__name__)

# Load Whisper model once
model = whisper.load_model("base")

# Replace with your Gemini API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    try:
        data = request.get_json()
        candidate_id = data.get("candidateId")
        video_filename = data.get("videoFilename")
        print(candidate_id, video_filename)
        if not candidate_id or not video_filename:
            return jsonify({"error": "Missing candidateId or videoFilename"}), 400

        video_path = os.path.join("/videos", video_filename)
        audio_path = video_path.replace(".mp4", ".flac")

        # Extract audio using ffmpeg
        extract_audio(video_path, audio_path)

        # Transcribe audio
        transcript = transcribe_audio(audio_path)

        # Analyze using Gemini
        analysis = analyze_with_gemini(transcript)

        return jsonify(analysis)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_audio(video_path, audio_path):
    command = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "flac", audio_path]
    subprocess.run(command, check=True)

def transcribe_audio(audio_path):
    result = model.transcribe(audio_path)
    return result["text"]

def analyze_with_gemini(transcript):
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)

    prompt = f"""You are an expert HR assistant that analyzes video introductions from job candidates. Analyze the following video transcript and provide a comprehensive assessment.

Video Transcript: "{transcript}"

Please analyze the candidate's communication and provide a detailed JSON response with the following structure:
{{
  "transcript": "{transcript}",
  "tone": "one of: Enthusiastic, Friendly, Nervous, Professional, Casual, Formal, Robotic",
  "confidence": "one of: High, Moderate, Low", 
  "clarity": "one of: Excellent, Good, Fair, Poor",
  "keywords": ["array of 5-8 important keywords and phrases from the speech"],
  "insights": ["array of 4-6 detailed observations about communication style, strengths, and areas for improvement"],
  "scores": {{
    "enthusiasm": number (0-100),
    "confidence": number (0-100),
    "clarity": number (0-100), 
    "professionalism": number (0-100)
  }},
  "communicationStrengths": ["array of 3-4 specific communication strengths"],
  "areasForImprovement": ["array of 2-3 areas where communication could be enhanced"],
  "overallAssessment": "2-3 sentence summary of the candidate's communication effectiveness"
}}"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    print("hello")
    response = model.generate_content(prompt)
    
    # Extract JSON
    try:
        print(response)
        text = response.text
        json_data = json.loads(extract_json_block(text))
        return json_data
    except Exception as e:
        return {
            "transcript": transcript,
            "error": "Failed to parse Gemini response",
            "raw": response.text,
            "fallback_reason": str(e)
        }

def extract_json_block(text):
    import re
    match = re.search(r"\{[\s\S]+\}", text)
    if not match:
        raise ValueError("No JSON found")
    return match.group(0)
from flask_cors import CORS
CORS(app)
if __name__ == "__main__":
    app.run(debug=True, port=5001)
