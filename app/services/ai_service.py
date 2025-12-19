import google.generativeai as genai
from app.core.config import settings
import json

# Configure Gemini
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_content(prompt: str) -> str:
    """
    Generates content using Gemini model.
    """
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini generation error: {e}")
        return "Analysis unavailable"

async def analyze_symptoms(symptoms: str) -> dict:
    """
    Analyzes symptoms using Gemini.
    """
    prompt = f"""
    Analyze the following patient symptoms and provide a preliminary analysis.
    Symptoms: {symptoms}
    
    Return the response in JSON format with the following keys:
    - severity: (low, moderate, high)
    - suggested_tests: list of strings
    - precautions: list of strings
    - possible_conditions: list of strings
    """
    try:
        content = await generate_content(prompt)
        # Clean markdown if present
        content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        print(f"Symptom analysis error: {e}")
        return {}

async def generate_insights(medical_data: dict) -> dict:
    """
    Generates insights for medical records.
    """
    prompt = f"""
    Generate medical insights based on the following record:
    {json.dumps(medical_data, default=str)}
    
    Return JSON with keys:
    - diagnosis_confidence: (low, medium, high)
    - treatment_recommendations: list of strings
    - risk_factors: list of strings
    - follow_up_priority: (routine, urgent)
    """
    try:
        content = await generate_content(prompt)
        content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        print(f"Insight generation error: {e}")
        return {}

async def interpret_lab_results(test_name: str, results: dict) -> str:
    """
    Interprets lab results.
    """
    prompt = f"""
    Interpret the following lab results for {test_name}:
    {json.dumps(results, default=str)}
    
    Provide a concise interpretation summary.
    """
    return await generate_content(prompt)

async def check_drug_interactions(medications: list) -> dict:
    """
    Checks for drug interactions.
    """
    prompt = f"""
    Check for drug interactions between the following medications:
    {", ".join(medications)}
    
    Return JSON with keys:
    - interactions: list of objects {{"drugs": [], "severity": "", "description": ""}}
    - safe: boolean
    """
    try:
        content = await generate_content(prompt)
        content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        print(f"Interaction check error: {e}")
        return {}

async def analyze_medical_image(image_url: str, prompt: str = "Analyze this medical image for abnormalities.") -> str:
    """
    Analyzes a medical image using Gemini (Vision capability).
    """
    try:
        # In a real scenario, we'd use Gemini 1.5 Flash/Pro with vision
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        # We need to fetch the image or pass it as parts. 
        # For simplicity, we'll instruct the model to analyze via the URL if supported 
        # or assume we download it first.
        
        response = model.generate_content([prompt, {"image_url": image_url}]) # Simplified API representation
        return response.text
    except Exception as e:
        print(f"Image analysis error: {e}")
        return "Image analysis unavailable"
