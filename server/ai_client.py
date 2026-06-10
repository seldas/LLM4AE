"""
Universal AI Client
Supports: OpenAI-compatible APIs (vLLM), Google Gemini, and FDA Elsa
Configuration via environment variables in .env file
"""

import os
import json
import requests
from urllib.parse import quote_plus
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
import urllib3

# Suppress SSL warnings for internal FDA systems
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()


class AIClient:
    """Universal AI client supporting multiple providers"""
    
    def __init__(self, provider="vllm"):
        """
        Initialize AI client with specified provider.
        
        Args:
            provider (str): One of 'vllm', 'gemini', or 'elsa'
        """
        self.provider = provider.lower()
        self._setup_client()
    
    def _setup_client(self):
        """Setup client based on provider"""
        if self.provider == "vllm":
            self.api_key = os.getenv('LLM_KEY', '')
            self.base_url = os.getenv('LLM_URL', '')
            self.model = os.getenv('LLM_MODEL', '')
            
            if not self.api_key:
                raise ValueError("LLM_KEY environment variable is not set")
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
        
        elif self.provider == "gemini":
            self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY', '')
            self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
            
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set")
            
            self.client = genai.Client(api_key=self.api_key)
        
        elif self.provider == "elsa":
            self.username = os.getenv('ELSA_API_NAME', '')
            self.password = os.getenv('ELSA_API_KEY', '')
            self.base_url = os.getenv('ELSA_BASE_URL', 'https://elsa-dev.preprod.fda.gov/Monolith/api/engine/runPixel')
            self.model = os.getenv('ELSA_MODEL_ENGINE_ID', '')
            
            if not self.username or not self.password:
                raise ValueError("ELSA_API_NAME and ELSA_API_KEY environment variables are not set")
            if not self.model:
                raise ValueError("ELSA_MODEL_ENGINE_ID environment variable is not set")
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'vllm', 'gemini', or 'elsa'")
    
    def call(self, message, system_prompt='Help answer the following requests.', 
             temperature=0.0, max_tokens=28000, **kwargs):
        """
        Universal call method for all providers.
        
        Args:
            message (str): User message/query
            system_prompt (str): System instruction
            temperature (float): Sampling temperature
            max_tokens (int): Maximum output tokens
            **kwargs: Additional provider-specific parameters
        
        Returns:
            str: Model response
        """
        if not message:
            return 'No input!'
        
        if self.provider == "vllm":
            return self._call_vllm(message, system_prompt, temperature, max_tokens, **kwargs)
        elif self.provider == "gemini":
            return self._call_gemini(message, system_prompt, temperature, max_tokens, **kwargs)
        elif self.provider == "elsa":
            return self._call_elsa(message, system_prompt, temperature, max_tokens, **kwargs)
    
    def _call_vllm(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """Call OpenAI-compatible API (vLLM)"""
        try:
            vllm_extras = {
                "repetition_penalty": kwargs.get("repetition_penalty", 1.1),
                "top_k": kwargs.get("top_k", 50),
            }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
                extra_body=vllm_extras,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"vLLM API error: {e}")
    
    def _call_gemini(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """Call Google Gemini API"""
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=kwargs.get("top_p", 0.95),
                max_output_tokens=max_tokens,
                system_instruction=system_prompt if system_prompt else None,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_ONLY_HIGH",
                    )
                ]
            )
            
            contents = [types.Content(
                role="user", 
                parts=[types.Part.from_text(text=message)]
            )]
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            return response.text or ""
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _call_elsa(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """Call FDA Elsa API"""
        try:
            # Combine system prompt and message for Elsa
            full_prompt = f"{system_prompt}\n\n{message}" if system_prompt else message
            
            # Construct Elsa command
            command = f'''LLM(engine = "{self.model}", command = "<encode>{full_prompt}</encode>", paramValues = [{{"max_completion_tokens": {max_tokens}, "temperature": {temperature}}}])'''
            
            response = requests.post(
                self.base_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=f'expression={quote_plus(command)}',
                auth=(self.username, self.password),
                verify=False  # For internal FDA systems with self-signed certs
            )
            
            if response.status_code == 200:
                result = json.loads(response.text)
                return result['pixelReturn'][0]['output']['response']
            else:
                raise Exception(f"Elsa API returned status {response.status_code}")
        except Exception as e:
            raise Exception(f"Elsa API error: {e}")


# Convenience function for quick usage
def call_ai(message, provider="vllm", system_prompt='Help answer the following requests.', 
            temperature=0.0, max_tokens=28000, **kwargs):
    """
    Convenience function to call AI without instantiating client.
    
    Args:
        message (str): User message/query
        provider (str): One of 'vllm', 'gemini', or 'elsa'
        system_prompt (str): System instruction
        temperature (float): Sampling temperature
        max_tokens (int): Maximum output tokens
        **kwargs: Additional provider-specific parameters
    
    Returns:
        str: Model response
    """
    client = AIClient(provider=provider)
    return client.call(message, system_prompt, temperature, max_tokens, **kwargs)
