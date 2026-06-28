import base64
import uuid
from openai import AsyncOpenAI
from imagekitio import ImageKit
from src.config.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

imagekit = ImageKit(

    private_key=settings.IMAGEKIT_PRIVATE_KEY,

)

class ImageGenerationService:
    @staticmethod
    async def generate_image(prompt: str, style_prompt: str, headshot_url: str = None) -> bytes:
        full_prompt = (
            f"{style_prompt}\n\n"
            f"User Request: {prompt}\n\n"
        )
        
        content = []
        if headshot_url:
            content.append({"type": "input_image",  "image_url":headshot_url})
        content.append({"type": "input_text", "text": full_prompt})
        
        response = await client.responses.create(
            model='gpt-5.4-mini',
            input=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            tools=[
                {
                    "type": "image_generation",
                    "model": "gpt-image-2",
                    "size": "1536x1024",
                    "quality": "high",
                    "output_format": "png",
                }
            ]
        )
        
        for item in response.output:
            if item.type == "image_generation_call" and item.result:
                return base64.b64decode(item.result)
        
        raise RuntimeError("No Image generation result found in the response")

    @staticmethod
    def upload_to_imagekit(image_bytes: bytes, filename: str) -> str:

      response = imagekit.files.upload(
        file=image_bytes,
        file_name=filename,
        folder="/grovii/scenes"
      )

      print(response)

      return response.url

    @staticmethod
    async def generate_and_upload_thumbnail(prompt: str, style_prompt: str, headshot_url: str = None) -> str:
        image_bytes = await ImageGenerationService.generate_image(prompt, style_prompt, headshot_url)
        filename = f"thumbnail_{uuid.uuid4().hex}.png"
        return ImageGenerationService.upload_to_imagekit(image_bytes, filename)

    @staticmethod
    async def generate_and_upload_scene_image(prompt: str, style_prompt: str) -> str:
        image_bytes = await ImageGenerationService.generate_image(prompt, style_prompt)
        filename = f"scene_{uuid.uuid4().hex}.png"
        return ImageGenerationService.upload_to_imagekit(image_bytes, filename)
