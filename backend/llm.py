import openai

from config import get_config


def get_openai_client() -> openai.OpenAI:
    config = get_config()
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return openai.OpenAI(api_key=config.openai_api_key, timeout=60.0)


def invoke_gpt4v(image_url: str, prompt: str) -> str:
    config = get_config()
    client = get_openai_client()
    
    response = client.chat.completions.create(
        model=config.vision_model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )
    
    return response.choices[0].message.content
