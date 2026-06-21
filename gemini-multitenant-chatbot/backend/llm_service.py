import os
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def generate_response(tenant_system_prompt: str, chat_history: list, new_message: str):
    """
    Generate a response from Gemini using system prompt and chat history.
    """
    # Use gemini-1.5-flash as the default model
    if tenant_system_prompt:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=tenant_system_prompt)
    else:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
    messages = []
    for msg in chat_history:
        messages.append({"role": msg.role, "parts": [msg.content]})
        
    messages.append({"role": "user", "parts": [new_message]})
    
    response = model.generate_content(messages)
    return response.text
