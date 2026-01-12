"""
Change classifier that assigns priority and validates quality
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import LLM clients
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)


class ChangeClassifier:
    """Classifies changes and assigns priority based on rules"""
    
    def __init__(self):
        """Initialize classifier with LLM client"""
        self.llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        self.model = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))
        
        if self.llm_provider == 'openai' and HAS_OPENAI:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.client = OpenAI(api_key=api_key)
            self.use_openai = True
        elif self.llm_provider == 'anthropic' and HAS_ANTHROPIC:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.client = Anthropic(api_key=api_key)
            self.use_openai = False
        else:
            raise ValueError(
                f"LLM provider '{self.llm_provider}' not available. "
                "Install openai or anthropic package and set API key."
            )
    
    def classify_change(self, change_data: Dict[str, Any], asset_type: str, 
                       url: str, change_type: str = None, 
                       summary: str = None, why_it_matters: str = None) -> Dict[str, Any]:
        """
        Classify a change and assign priority
        
        Args:
            change_data: Change data from diff engine
            asset_type: Type of asset (pricing, features, etc.)
            url: URL of the asset
            change_type: Existing change type (if already classified)
            summary: Existing summary (if already generated)
            why_it_matters: Existing "why it matters" (if already generated)
        
        Returns:
            Dictionary with:
                - priority: high, medium, or low
                - change_type: Type of change
                - summary: Refined summary (≤3 sentences)
                - why_it_matters: Why this change matters
                - confidence: Confidence score (0-1)
        """
        # Build context for classification
        structured_diff = change_data.get('structured_diff')
        text_diff = change_data.get('text_diff', {})
        change_percentage = change_data.get('content_change_percentage', 0.0)
        
        # Prepare prompt
        prompt = self._build_classification_prompt(
            asset_type, url, change_type, summary, why_it_matters,
            structured_diff, text_diff, change_percentage
        )
        
        try:
            if self.use_openai:
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            
            result = self._parse_classification_response(response)
            
            # Validate and refine result
            result = self._validate_classification(result, change_data)
            
            return result
        except Exception as e:
            logger.error(f"Error classifying change: {e}", exc_info=True)
            # Fallback to rule-based classification
            return ChangeClassifier._rule_based_classification_static(change_data, asset_type, change_type)
    
    def _build_classification_prompt(self, asset_type: str, url: str,
                                     change_type: str, summary: str,
                                     why_it_matters: str, structured_diff: Dict,
                                     text_diff: Dict, change_percentage: float) -> str:
        """Build prompt for classification"""
        
        # Priority rules from architecture
        priority_rules = """
PRIORITY RULES:
- HIGH: Pricing changes, free tier introduction/removal, major feature launches, 
        security/compliance certifications, major integrations
- MEDIUM: Changelog updates, press releases, new case studies, new customer logos
- LOW: Homepage/landing page copy changes, general industry blog posts, testimonials
"""
        
        # Build context about the change
        context_parts = []
        
        if structured_diff:
            context_parts.append(f"Structured changes: {json.dumps(structured_diff, indent=2)}")
        
        if text_diff:
            added = text_diff.get('added_count', 0)
            removed = text_diff.get('removed_count', 0)
            context_parts.append(f"Text changes: {added} lines added, {removed} lines removed")
        
        context_parts.append(f"Content change: {change_percentage}%")
        
        if change_type:
            context_parts.append(f"Change type (preliminary): {change_type}")
        
        if summary:
            context_parts.append(f"Summary (preliminary): {summary}")
        
        if why_it_matters:
            context_parts.append(f"Why it matters (preliminary): {why_it_matters}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a competitive intelligence analyst classifying changes to competitor websites.

Asset Type: {asset_type}
URL: {url}

{priority_rules}

Change Details:
{context}

Your task:
1. Assign priority (high, medium, or low) based on the rules above
2. Confirm or refine the change type
3. Ensure summary is ≤3 sentences and follows "Before → After" format
4. Ensure "why it matters" is specific, non-speculative, and actionable
5. Provide confidence score (0.0-1.0) for your classification

Respond in JSON format:
{{
    "priority": "high|medium|low",
    "change_type": "pricing|feature|compliance|changelog|sitemap|blog|content|other",
    "summary": "Refined summary (≤3 sentences, Before → After format)",
    "why_it_matters": "Specific, non-speculative explanation of why this matters",
    "confidence": 0.0-1.0
}}
"""
        
        return prompt
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a competitive intelligence analyst. Classify changes and provide structured JSON responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=self.temperature,
            system="You are a competitive intelligence analyst. Classify changes and provide structured JSON responses.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM classification response"""
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['priority', 'change_type', 'summary', 'why_it_matters', 'confidence']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing field '{field}' in classification response")
                    if field == 'confidence':
                        result[field] = 0.5  # Default confidence
                    elif field == 'priority':
                        result[field] = 'medium'  # Default priority
                    else:
                        result[field] = 'unknown'
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            raise
    
    def _validate_classification(self, result: Dict[str, Any], change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and refine classification result"""
        # Ensure priority is valid
        priority = result.get('priority', 'medium').lower()
        if priority not in ['high', 'medium', 'low']:
            priority = 'medium'
        result['priority'] = priority
        
        # Ensure summary is ≤3 sentences
        summary = result.get('summary', '')
        sentences = summary.split('. ')
        if len(sentences) > 3:
            # Truncate to 3 sentences
            summary = '. '.join(sentences[:3])
            if not summary.endswith('.'):
                summary += '.'
            result['summary'] = summary
        
        # Ensure confidence is in valid range
        confidence = float(result.get('confidence', 0.5))
        result['confidence'] = max(0.0, min(1.0, confidence))
        
        return result
    
    @staticmethod
    def _rule_based_classification_static(change_data: Dict[str, Any], 
                                         asset_type: str, change_type: str = None) -> Dict[str, Any]:
        """Fallback rule-based classification when LLM is unavailable"""
        structured_diff = change_data.get('structured_diff')
        
        # Determine priority based on change type and structured diff
        priority = 'medium'  # Default
        
        if change_type == 'pricing' or (structured_diff and 'tier_changes' in structured_diff):
            priority = 'high'
        elif change_type == 'compliance' or (structured_diff and 'new_certifications' in structured_diff):
            priority = 'high'
        elif change_type == 'feature' and structured_diff:
            features_added = structured_diff.get('features_added', [])
            if len(features_added) > 0:
                priority = 'high'
        elif change_type == 'changelog':
            priority = 'medium'
        elif change_type == 'blog' or change_type == 'content':
            priority = 'low'
        
        # Generate basic summary
        change_percentage = change_data.get('content_change_percentage', 0.0)
        summary = f"Change detected on {asset_type} page ({change_percentage}% change)"
        
        why_it_matters = f"Monitor {asset_type} changes for competitive intelligence"
        
        return {
            'priority': priority,
            'change_type': change_type or asset_type,
            'summary': summary,
            'why_it_matters': why_it_matters,
            'confidence': 0.6  # Lower confidence for rule-based
        }

