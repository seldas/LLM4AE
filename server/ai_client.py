"""
Universal AI Client
Supports: FDA Elsa (Claude 4.6 Sonnet), OpenAI / vLLM / Ollama (Llama 4), and Google Gemini
Configuration via environment variables in .env file
"""

import os
import json
import time
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
            provider (str): One of 'vllm', 'openai', 'ollama', 'elsa', 'sonnet', 'claude', or 'gemini'
        """
        self.provider = provider.lower()
        self._setup_client()
    
    def _setup_client(self):
        """Setup client based on provider"""
        if self.provider in ("vllm", "openai", "ollama", "llama4"):
            self.api_key = os.getenv('LLM_KEY', '') or os.getenv('OPENAI_API_KEY', 'dummy_key')
            self.base_url = os.getenv('LLM_URL', '') or os.getenv('OPENAI_BASE_URL', '')
            self.model = os.getenv('LLM_MODEL', 'llama-4-maverick')
            
            if not self.api_key and self.provider != "ollama":
                raise ValueError("LLM_KEY or OPENAI_API_KEY environment variable is not set")
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
        
        elif self.provider in ("elsa", "sonnet", "claude", "claude_46_sonnet"):
            # For this study, Claude 4.6 Sonnet is implemented directly through FDA Elsa
            self.username = os.getenv('ELSA_API_NAME', '')
            self.password = os.getenv('ELSA_API_KEY', '')
            self.base_url = os.getenv('ELSA_BASE_URL', 'https://elsa-dev.preprod.fda.gov/Monolith/api/engine/runPixel')
            self.model = os.getenv('ELSA_MODEL_ID', '') or os.getenv('ELSA_MODEL_ENGINE_ID', '')
            self.model_name = os.getenv('ELSA_MODEL_NAME', 'CLAUDE_46_SONNET')
            
            if not self.username or not self.password:
                raise ValueError("ELSA_API_NAME and ELSA_API_KEY environment variables are not set")
            if not self.model:
                raise ValueError("ELSA_MODEL_ID or ELSA_MODEL_ENGINE_ID environment variable is not set")
        
        elif self.provider == "gemini":
            self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY', '')
            self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
            
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set")
            
            self.client = genai.Client(api_key=self.api_key)
        
        elif self.provider == "anthropic":
            # Direct Anthropic fallback if configured, otherwise routes to Elsa
            self.api_key = os.getenv('ANTHROPIC_API_KEY', '')
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
            self.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com/v1/messages')
            
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Use 'vllm', 'elsa' (Sonnet 4.6), 'gemini', or 'openai'")
    
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
        
        if self.provider in ("vllm", "openai", "ollama", "llama4"):
            return self._call_vllm(message, system_prompt, temperature, max_tokens, **kwargs)
        elif self.provider in ("elsa", "sonnet", "claude", "claude_46_sonnet"):
            return self._call_elsa(message, system_prompt, temperature, max_tokens, **kwargs)
        elif self.provider == "gemini":
            return self._call_gemini(message, system_prompt, temperature, max_tokens, **kwargs)
        elif self.provider == "anthropic":
            return self._call_anthropic(message, system_prompt, temperature, max_tokens, **kwargs)
    
    def _call_vllm(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """Call OpenAI-compatible API (vLLM / Ollama / OpenAI)"""
        try:
            vllm_extras = {
                "repetition_penalty": kwargs.get("repetition_penalty", 1.1),
                "top_k": kwargs.get("top_k", 50),
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
                extra_body=vllm_extras,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"vLLM/OpenAI API error: {e}")
    
    def _call_elsa(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """
        Call FDA Elsa API (Claude 4.6 Sonnet).
        Implements URL-encoded Pixel LLM invocation and automatic retry handling.
        """
        full_prompt = f"{system_prompt}\n\n{message}" if system_prompt else message
        
        command = (
            f'LLM(engine = "{self.model}", command = "<encode>{full_prompt}</encode>", '
            f'paramValues = [{{"max_completion_tokens": {max_tokens}, "temperature": {temperature}}}])'
        )
        payload = f'expression={quote_plus(command)}'
        
        timeout = kwargs.get("timeout", 600.0)
        retries = kwargs.get("retries", 3)
        retry_backoff = kwargs.get("retry_backoff", 2.0)
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    self.base_url,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=payload,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=timeout
                )
                
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                    
                if response.status_code == 200:
                    result = json.loads(response.text)
                    return result['pixelReturn'][0]['output']['response']
                else:
                    raise Exception(f"Elsa API returned HTTP {response.status_code}: {response.text[:1000]}")
            except Exception as e:
                last_error = e
                if attempt < retries:
                    sleep_time = retry_backoff * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    break
                    
        raise Exception(f"Elsa API error after {retries + 1} attempts: {last_error}")
    
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
    
    def _call_anthropic(self, message, system_prompt, temperature, max_tokens, **kwargs):
        """Direct Anthropic API fallback"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": self.model,
                "max_tokens": min(max_tokens, 8192),
                "temperature": temperature,
                "messages": [{"role": "user", "content": message}]
            }
            if system_prompt:
                payload["system"] = system_prompt
                
            resp = requests.post(self.base_url, headers=headers, json=payload, timeout=kwargs.get("timeout", 600.0))
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [])
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "".join(text_parts)
            else:
                raise Exception(f"Anthropic API error HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")


# Convenience function for quick usage
def call_ai(message, provider="vllm", system_prompt='Help answer the following requests.', 
            temperature=0.0, max_tokens=28000, **kwargs):
    """
    Convenience function to call AI without instantiating client.
    
    Args:
        message (str): User message/query
        provider (str): One of 'vllm', 'elsa' (Claude 4.6 Sonnet), 'gemini', or 'openai'
        system_prompt (str): System instruction
        temperature (float): Sampling temperature
        max_tokens (int): Maximum output tokens
        **kwargs: Additional provider-specific parameters
    
    Returns:
        str: Model response
    """
    client = AIClient(provider=provider)
    return client.call(message, system_prompt, temperature, max_tokens, **kwargs)


