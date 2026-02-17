# llm.py
# Wrapper for LLM API calls - supports Anthropic, OpenAI, and Grok

from config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    GROK_API_KEY,
    LLM_MODELS,
    LLM_MAX_TOKENS,
)


def ask_llm(prompt, system_prompt=None):
    """
    Send a prompt to the configured LLM and get a response.
    
    Args:
        prompt: The user message/question
        system_prompt: Optional system instructions
    
    Returns:
        The text response from the LLM
    """
    if LLM_PROVIDER == "anthropic":
        return _ask_anthropic(prompt, system_prompt)
    elif LLM_PROVIDER == "openai":
        return _ask_openai(prompt, system_prompt)
    elif LLM_PROVIDER == "grok":
        return _ask_grok(prompt, system_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")


def _ask_anthropic(prompt, system_prompt=None):
    """Anthropic Claude API"""
    import anthropic
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    kwargs = {
        "model": LLM_MODELS["anthropic"],
        "max_tokens": LLM_MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    
    if system_prompt:
        kwargs["system"] = system_prompt
    
    response = client.messages.create(**kwargs)
    return response.content[0].text


def _ask_openai(prompt, system_prompt=None):
    """OpenAI GPT API"""
    from openai import OpenAI
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=LLM_MODELS["openai"],
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,
    )
    return response.choices[0].message.content


def _ask_grok(prompt, system_prompt=None):
    """xAI Grok API (OpenAI-compatible)"""
    from openai import OpenAI
    
    # Grok uses OpenAI-compatible API with different base URL
    client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.x.ai/v1",
    )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=LLM_MODELS["grok"],
        max_tokens=LLM_MAX_TOKENS,
        messages=messages,
    )
    return response.choices[0].message.content


# Test if run directly
if __name__ == "__main__":
    print(f"Testing {LLM_PROVIDER}...")
    response = ask_llm("Say 'API connection working!' and nothing else.")
    print(response)
