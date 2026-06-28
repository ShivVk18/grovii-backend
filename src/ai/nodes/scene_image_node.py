from src.services.image_generation_service import ImageGenerationService

async def scene_image_node(state):
    scenes = state.get("scenes", [])
    style = state.get("style", "")
    
    for i, scene in enumerate(scenes):
        scene_prompt = f"Scene {i+1}: {scene.get('description', '')}. Visuals: {scene.get('visual_cue', '')}"
        style_prompt = f"Style: {style}. Photorealistic, high quality, cinematic lighting."
        
        try:
            image_url = await ImageGenerationService.generate_and_upload_scene_image(scene_prompt, style_prompt)
            scene["scene_image_url"] = image_url
            scene["image_status"] = "completed"
        except Exception as e:
            print(f"Error generating image for scene {i+1}: {e}")
            scene["scene_image_url"] = None
            scene["image_status"] = "failed"
            
    state["scenes"] = scenes
    return state
