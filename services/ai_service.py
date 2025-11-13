from groq import Groq
import os
from typing import Dict, Any, List
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Please set it in your .env file"
    )

# Initialize Groq client  openai/gpt-oss-120b
client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are an AI wellness companion focused on mental wellness and cognitive enhancement. 

Your core responsibilities:
1. Provide supportive, warm, and professional responses
2. Stay strictly within wellness and cognitive enhancement domains
3. Consider the user's profile and conversation history for personalized responses
4. For off-topic questions, gently redirect to wellness topics
5. NEVER provide medical diagnosis or treatment advice - always suggest consulting healthcare professionals

User Profile:
- Age: {age}
- Background: {background}
- Preferences: {preferences}

Past Conversation Summaries:
{summaries}

Recent Conversation Context:
{chat_history}

Guidelines:
- Use empathetic and encouraging language
- Suggest evidence-based wellness practices
- Encourage healthy habits and self-care
- Recognize when professional help may be needed
- Keep responses concise but meaningful (2-4 paragraphs)

Remember: You're a supportive companion, not a medical professional."""

# Summary generation prompt
SUMMARY_PROMPT_TEMPLATE = """Analyze the following conversation and create a concise summary.

Conversation:
{conversation}

Provide a summary in the following JSON format:
{{
  "summary": "A brief 2-3 sentence summary of the entire conversation",
  "key_topics": ["topic1", "topic2", "topic3"],
  "sentiment": "positive/neutral/concerned",
  "insights": "Key insights about the user's wellness journey"
}}

Focus on:
- Main wellness concerns discussed
- Progress or patterns noticed
- User's emotional state
- Important context for future conversations

Respond ONLY with valid JSON, no additional text."""

# Wellness keywords for context extraction
WELLNESS_KEYWORDS = [
    'stress', 'anxiety', 'worried', 'nervous', 'tired', 'exhausted',
    'sleep', 'insomnia', 'pain', 'headache', 'energy', 'fatigue',
    'focus', 'concentration', 'memory', 'mood', 'depression', 'sad',
    'exercise', 'workout', 'diet', 'nutrition', 'meditation', 'mindfulness',
    'breathing', 'relaxation', 'burnout', 'overwhelmed', 'tension',
    'happy', 'grateful', 'motivated', 'calm', 'peaceful', 'confident'
]


def extract_keywords(text: str) -> List[str]:
    """Extract wellness-related keywords from text"""
    text_lower = text.lower()
    found_keywords = [kw for kw in WELLNESS_KEYWORDS if kw in text_lower]
    return list(set(found_keywords))  # Remove duplicates


def format_chat_history(conversation_items: List[Dict[str, Any]], limit: int = 10) -> str:
    """Format conversation history for context"""
    if not conversation_items:
        return "No previous conversation."
    
    # Sort by timestamp and take last N items
    sorted_items = sorted(conversation_items, key=lambda x: x.get('timestamp', ''))
    recent_items = sorted_items[-limit:]
    
    formatted = []
    for item in recent_items:
        role = item.get('role', 'unknown').capitalize()
        content = item.get('content', '')
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)


def format_summaries(summaries: List[Dict[str, Any]]) -> str:
    """Format past conversation summaries for context"""
    if not summaries:
        return "No previous conversation summaries."
    
    formatted = []
    for idx, summary in enumerate(summaries[-3:], 1):  # Last 3 summaries
        formatted.append(f"Summary {idx}:")
        formatted.append(f"- {summary.get('summary', 'N/A')}")
        formatted.append(f"- Topics: {', '.join(summary.get('key_topics', []))}")
        formatted.append(f"- Sentiment: {summary.get('sentiment', 'N/A')}")
        formatted.append("")
    
    return "\n".join(formatted)


def build_prompt(
    user_message: str,
    profile: Dict[str, Any],
    conversation_history: List[Dict[str, Any]]
) -> tuple[str, str]:
    """Build the system prompt and user message for the AI model"""
    
    age = profile.get('age', 'Not specified')
    background = profile.get('background', 'Not specified')
    preferences = profile.get('preferences', {})
    summaries = profile.get('summaries', [])
    
    # Format preferences nicely
    pref_str = ', '.join([k for k, v in preferences.items() if v]) if preferences else 'Not specified'
    
    chat_history = format_chat_history(conversation_history)
    summaries_str = format_summaries(summaries)
    
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        age=age,
        background=background,
        preferences=pref_str,
        summaries=summaries_str,
        chat_history=chat_history
    )
    
    return system_prompt, user_message


async def generate_response(
    user_message: str,
    profile: Dict[str, Any],
    conversation_history: List[Dict[str, Any]]
) -> str:
    """Generate AI response using Groq (Llama 3.3)"""
    
    try:
        system_prompt, user_msg = build_prompt(user_message, profile, conversation_history)
        
        # Call Groq API with Llama 3.3
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ],
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
            stream=False
        )
        
        response_text = chat_completion.choices[0].message.content
        return response_text.strip()
        
    except Exception as e:
        raise Exception(f"Groq API error: {str(e)}")


async def generate_conversation_summary(conversation_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary of the conversation using Groq (Llama 3.3)"""
    
    try:
        # Format conversation for summary
        conversation_text = []
        for item in conversation_items:
            role = item.get('role', 'unknown').capitalize()
            content = item.get('content', '')
            conversation_text.append(f"{role}: {content}")
        
        conversation_str = "\n".join(conversation_text)
        
        prompt = SUMMARY_PROMPT_TEMPLATE.format(conversation=conversation_str)
        
        # Generate summary using Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of wellness conversations in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=MODEL_NAME,
            temperature=0.5,
            max_tokens=512,
            top_p=0.9,
            stream=False
        )
        
        summary_text = chat_completion.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if "```json" in summary_text:
                summary_text = summary_text.split("```json")[1].split("```")[0].strip()
            elif "```" in summary_text:
                summary_text = summary_text.split("```")[1].split("```")[0].strip()
            
            summary_data = json.loads(summary_text)
        except:
            # If parsing fails, create a basic summary
            summary_data = {
                "summary": summary_text[:200],
                "key_topics": extract_keywords(conversation_str)[:5],
                "sentiment": "neutral",
                "insights": "Conversation analysis available"
            }
        
        return summary_data
        
    except Exception as e:
        # Return a basic summary if generation fails
        all_keywords = []
        for item in conversation_items:
            all_keywords.extend(extract_keywords(item.get('content', '')))
        
        return {
            "summary": "Conversation covered wellness and personal growth topics",
            "key_topics": list(set(all_keywords))[:5],
            "sentiment": "neutral",
            "insights": f"Generated from {len(conversation_items)} messages"
        }


def validate_message(message: str) -> bool:
    """Validate user message"""
    if not message or not message.strip():
        return False
    if len(message) > 5000:
        return False
    return True
