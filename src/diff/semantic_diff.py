"""
Semantic diff using LLM to identify meaningful changes
"""
import os
from typing import Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import OpenAI, fall back to Anthropic if not available
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


class SemanticDiff:
    """Use LLM to perform semantic analysis of changes"""
    
    def __init__(self):
        """Initialize semantic diff with LLM client"""
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
    
    def analyze_change(self, before_content: str, after_content: str, 
                      asset_type: str, url: str) -> Dict[str, Any]:
        """
        Use LLM to analyze change and extract meaningful information
        
        Args:
            before_content: Previous content
            after_content: Current content
            asset_type: Type of asset (pricing, features, etc.)
            url: URL of the asset
        
        Returns:
            Dictionary with semantic analysis results
        """
        prompt = self._build_prompt(before_content, after_content, asset_type, url)
        
        try:
            if self.use_openai:
                response = self._call_openai(prompt)
            else:
                response = self._call_anthropic(prompt)
            
            return self._parse_response(response)
        except Exception as e:
            # If LLM call fails, return basic analysis
            return {
                'summary': f"Change detected on {asset_type} page",
                'change_type': 'unknown',
                'significance': 'medium',
                'error': str(e)
            }
    
    def _build_prompt(self, before_content: str, after_content: str, 
                     asset_type: str, url: str) -> str:
        """Build prompt for LLM"""
        # Truncate content if too long (LLM context limits)
        max_length = 5000
        if len(before_content) > max_length:
            before_content = before_content[:max_length] + "... [truncated]"
        if len(after_content) > max_length:
            after_content = after_content[:max_length] + "... [truncated]"
        
        prompt = f"""You are analyzing changes to a competitor's {asset_type} page.

URL: {url}
Asset Type: {asset_type}

BEFORE (previous version):
{before_content}

AFTER (current version):
{after_content}

Analyze these changes and provide:
1. A brief summary (≤3 sentences) describing what changed (Before → After format)
2. The type of change (pricing, feature, compliance, content, other)
3. Why this change matters for competitive intelligence (be specific and non-speculative)
4. Significance level (high, medium, low)

Respond in JSON format:
{{
    "summary": "Brief summary of the change",
    "change_type": "pricing|feature|compliance|content|other",
    "why_it_matters": "Specific reason why this change is important",
    "significance": "high|medium|low"
}}
"""
        
        return prompt
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a competitive intelligence analyst. Analyze changes and provide structured JSON responses."},
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
            system="You are a competitive intelligence analyst. Analyze changes and provide structured JSON responses.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response"""
        import json
        
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                # Remove code block markers
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract key information
            return {
                'summary': response_text[:200] + "..." if len(response_text) > 200 else response_text,
                'change_type': 'unknown',
                'significance': 'medium',
                'error': 'Failed to parse JSON response'
            }
    
    def filter_noise(self, change_data: Dict[str, Any], semantic_analysis: Dict[str, Any]) -> bool:
        """
        Determine if change should be filtered out as noise
        
        Args:
            change_data: Change data from diff engine
            semantic_analysis: Analysis from LLM
        
        Returns:
            True if change should be filtered (is noise), False if it's meaningful
        """
        # If LLM says it's low significance and change percentage is small, filter
        significance = semantic_analysis.get('significance', 'medium').lower()
        change_percentage = change_data.get('content_change_percentage', 0.0)
        
        if significance == 'low' and change_percentage < 2.0:
            return True  # Filter out
        
        # If change type is "other" and percentage is very small, might be noise
        change_type = semantic_analysis.get('change_type', '').lower()
        if change_type == 'other' and change_percentage < 1.0:
            return True  # Filter out
        
        return False  # Keep the change

