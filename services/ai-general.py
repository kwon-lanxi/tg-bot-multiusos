from openai import OpenAI
from pydantic import BaseModel


class AIService:
  def __init__(self, api_key: str, url_base: str = "https://api.openai.com/v1"):
    self.client = OpenAI(api_key=api_key, base_url=url_base)

  def structure_response(self,reasoning: str,pydinamic_structure: type[BaseModel],prompt: str,model: str,tools: list | None = None,system_message: str = "You are a helpful assistant.") -> BaseModel: 
    response = self.client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        response_format=pydinamic_structure,
        tools=tools,
        reasoning_effort=reasoning
    )

    return response.choices[0].message.parsed

  def generate_image(self,prompt: str,model: str = "dall-e-3",size: str = None,n: int = 1) -> list[str]:
        response = self.client.images.generate(
            model=model,
            prompt=prompt,
            output_format="png",
            size=size,
            n=n,
            response_format="url"
        )
        return [data.url for data in response.data]
    
  def speech_audio_to_text(self,audio_file_path: str,model: str = "whisper-1") -> str:
        with open(audio_file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=model,
                file=audio_file
            )
        return response.text