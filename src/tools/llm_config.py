from typing import Dict, Any
from config.settings import OPENAI_API_KEY, anthropic_api_key

def get_llm_config(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration based on the selected model type.    
    Args:
        llm_type (str): Type of LLM to use ('gpt4', 'claude')        
    Returns:
        dict: LLM configuration dictionary
    """
    llm_configs = {
        'gpt4o-mini': {
            "model": "gpt-4o-mini",
            'api_key': OPENAI_API_KEY,
            'temperature':0,
            "cache_seed": 0,
        },
        'gpt-4.1': {
            "model": "gpt-4.1",
            'api_key': OPENAI_API_KEY,
            'temperature':0,
            "cache_seed": 0,
        },
        'gpt4o': {
            "model": "gpt-4o",
            'api_key': OPENAI_API_KEY,
            'temperature':0,
           # "cache_seed": 0,
        },
        'o3-mini': {
            "model": "o3-mini",
            'api_key': OPENAI_API_KEY,
            #'temperature':0,
           # "cache_seed": 0,
        },
        'claude_35': {
            "model": "claude-3-5-sonnet-20240620",
            'api_key': anthropic_api_key,
            'api_type': 'anthropic',
            'temperature':0,
            "cache_seed": 0,
   
        },
        'ArgoLLMs': {  # Local client operates only within the organization
            "model": "gpto1preview",
            "model_client_cls": "ArgoModelClient",
            'temperature': 0,
            "cache_seed": 0,
        }
    }
    
    return llm_configs.get(llm_type, llm_configs['ArgoLLMs'])