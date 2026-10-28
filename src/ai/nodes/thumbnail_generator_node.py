from src.services.image_generation_service import ImageGenerationService
from src.config.log_safety import safe_error

async def thumbnail_generator_node(state):
    script = state.get("script", "")
    hook = state.get("hook", "")
    tone = state.get("tone", "")
    style = state.get("style", "")
    
    prompt = f"Create a YouTube thumbnail. Hook: {hook}. Script: {script[:200]}..."
    style_prompt = f"Tone: {tone}. Style: {style}. High detail, cinematic, 4k."
    
    try:
        thumbnail_url = await ImageGenerationService.generate_and_upload_thumbnail(prompt, style_prompt)
        state["thumbnail_url"] = thumbnail_url
    except Exception as e:
        print(f"Error generating thumbnail: {safe_error(e)}")
        state["thumbnail_url"] = None

    return state
