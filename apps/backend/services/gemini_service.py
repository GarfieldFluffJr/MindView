"""Gemini API integration for AI-powered case feedback."""
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from config import settings


# Configure the Gemini API
def get_gemini_model():
    """Get configured Gemini model."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not configured. Add it to your .env file.")

    genai.configure(api_key=settings.gemini_api_key)
    # Using gemini-1.5-flash for free tier
    return genai.GenerativeModel('gemini-1.5-flash')


SYSTEM_PROMPT = """You are a medical AI assistant helping neurologists and radiologists analyze brain MRI scans.
You provide clear, professional, and actionable insights based on imaging data and calculated metrics.

Important guidelines:
- Use clear, accessible language that medical professionals can easily understand
- Always emphasize that AI analysis should be verified by qualified medical professionals
- Provide evidence-based recommendations when possible
- Be thorough but concise
- Highlight any concerning findings that may require urgent attention
- When discussing tumor progression, reference relevant medical guidelines (WHO, RANO criteria)
- Include specific measurements and percentages when available
"""


def generate_case_summary_prompt(
    patient_id: int,
    case_id: int,
    scan_summaries: List[Dict[str, Any]],
    aggregated_metrics: Dict[str, Any]
) -> str:
    """Generate the prompt for case summary."""

    scan_info = ""
    for i, scan in enumerate(scan_summaries, 1):
        scan_info += f"""
Scan {i}: {scan.get('filename', 'Unknown')}
- Date: {scan.get('scan_date', 'Unknown')}
- Tumor Detected: {'Yes' if scan.get('has_tumor') else 'No'}
- Regions: {', '.join(scan.get('regions_detected', [])) if scan.get('regions_detected') else 'N/A'}
"""
        if scan.get('metrics'):
            metrics = scan['metrics']
            if metrics.get('total_lesion_volume_mm3'):
                scan_info += f"- Total Lesion Volume: {metrics['total_lesion_volume_mm3']:.2f} mm³\n"
            if metrics.get('active_enhancing_volume_mm3'):
                scan_info += f"- Enhancing Volume: {metrics['active_enhancing_volume_mm3']:.2f} mm³\n"
            if metrics.get('edema_volume_mm3'):
                scan_info += f"- Edema Volume: {metrics['edema_volume_mm3']:.2f} mm³\n"
            if metrics.get('midline_shift_mm'):
                scan_info += f"- Midline Shift: {metrics['midline_shift_mm']:.2f} mm\n"

    prompt = f"""Please analyze this brain MRI case and provide a comprehensive summary.

CASE INFORMATION:
- Patient ID: {patient_id}
- Case ID: {case_id}
- Total Scans: {len(scan_summaries)}

SCAN HISTORY:
{scan_info}

AGGREGATED METRICS:
{json.dumps(aggregated_metrics, indent=2)}

Please provide:

1. **Case Overview**: Brief summary of the case and overall findings

2. **Tumor Analysis** (if applicable):
   - Current tumor characteristics
   - Progression assessment comparing scans over time
   - Volume changes and growth rate estimation

3. **Key Observations**:
   - Notable findings from each scan
   - Changes between scans
   - Areas of concern

4. **Clinical Considerations**:
   - Potential implications based on imaging
   - Relevant WHO/RANO criteria considerations
   - Factors that may affect prognosis

5. **Recommendations**:
   - Suggested follow-up timeline
   - Additional imaging considerations
   - Precautionary measures

6. **Important Notes**:
   - Any urgent findings requiring immediate attention
   - Limitations of this AI analysis

Please format your response in a clear, readable manner using markdown.
"""
    return prompt


async def generate_summary(
    patient_id: int,
    case_id: int,
    scan_summaries: List[Dict[str, Any]],
    aggregated_metrics: Dict[str, Any]
) -> str:
    """Generate an AI summary for the case."""
    model = get_gemini_model()

    prompt = generate_case_summary_prompt(
        patient_id, case_id, scan_summaries, aggregated_metrics
    )

    chat = model.start_chat(history=[
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "model", "parts": ["I understand. I'm ready to help analyze brain MRI cases with clear, professional insights while emphasizing the importance of verification by qualified medical professionals."]}
    ])

    response = await chat.send_message_async(prompt)

    # Check if response has valid content
    if not response.candidates or len(response.candidates) == 0:
        raise ValueError("Gemini API returned no response candidates")

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        # Check finish reason for more context
        finish_reason = getattr(candidate, 'finish_reason', None)
        if finish_reason:
            raise ValueError(f"Gemini API returned empty response (finish_reason: {finish_reason})")
        raise ValueError("Gemini API returned empty response")

    return candidate.content.parts[0].text


async def chat_response(
    messages: List[Dict[str, str]],
    case_context: Dict[str, Any]
) -> str:
    """Generate a chat response based on conversation history."""
    model = get_gemini_model()

    # Build context message
    context = f"""Current case context:
- Patient ID: {case_context.get('patient_id')}
- Case ID: {case_context.get('case_id')}
- Number of scans: {case_context.get('scan_count', 0)}
- Has tumor: {case_context.get('has_tumor', False)}
"""

    if case_context.get('metrics'):
        context += f"\nMetrics: {json.dumps(case_context['metrics'], indent=2)}"

    # Build chat history
    history = [
        {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + context]},
        {"role": "model", "parts": ["I understand the case context. I'm ready to discuss this patient's brain imaging findings and answer any questions."]}
    ]

    # Add previous messages
    for msg in messages[:-1]:  # All but the last (current) message
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=history)

    # Send the current message
    current_message = messages[-1]["content"] if messages else ""
    response = await chat.send_message_async(current_message)

    # Check if response has valid content
    if not response.candidates or len(response.candidates) == 0:
        raise ValueError("Gemini API returned no response candidates")

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        finish_reason = getattr(candidate, 'finish_reason', None)
        if finish_reason:
            raise ValueError(f"Gemini API returned empty response (finish_reason: {finish_reason})")
        raise ValueError("Gemini API returned empty response")

    return candidate.content.parts[0].text
