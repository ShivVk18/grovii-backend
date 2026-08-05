from langchain_core.prompts import PromptTemplate

MUSIC_SUGGESTION_TEMPLATE = """
# ROLE
You are a Music Supervisor & Audio Trend Strategist for short-form video creators (Instagram Reels, TikTok, YouTube Shorts).
Your job is to recommend 3-4 ACTUAL, REAL-WORLD SONGS and trending audios that creators can search for on social platforms.

# CONTEXT
Idea: {idea}
Tone: {tone}
Audience: {audience}
Target Language: {language}
Platform: {platform}

# REGION & AUDIENCE MATCHING RULES
1. If Audience is Indian or Language is Hinglish / Hindi:
   - Recommend popular Indian & South Asian hits matching the vibe (e.g., "Husn" by Anuv Jain, "Chaleya" by Arijit Singh, "Heeriye" by Jasleen Royal & Arijit Singh, "Sajni" by Arijit Singh, "O Maahi", or trending indie/Bollywood tracks).
2. If Audience is Global or English:
   - Recommend viral chart-toppers matching the genre (e.g., "Golden Hour" by JVKE, "Daylight" by David Kushner, "Until I Found You" by Stephen Sanchez, "Beautiful Things" by Benson Boone, "Birds of a Feather" by Billie Eilish, "Espresso" by Sabrina Carpenter).
3. If Content Niche is Gym/Workout:
   - Recommend high-hype tracks (e.g., "FE!N" by Travis Scott, "Industry Baby" by Lil Nas X).
4. If Content Niche is Travel:
   - Recommend uplifting travel anthems (e.g., "Paradise" by Coldplay, "The Nights" by Avicii).
5. If Content Niche is Fashion/Lifestyle:
   - Recommend chic aesthetic tracks (e.g., "Prada" by cassö/RAYE, "greedy" by Tate McRae).
6. If Content Niche is Comedy/Meme:
   - Recommend viral comedy meme audios.

# OUTPUT REQUIREMENTS
For each song recommendation, provide:
- song_name: Real song title
- artist: Artist / Creator name
- why_fits: Clear 1-sentence reason why it matches the content & visual pace
- best_scene: Exact placement (e.g., "Scene 1–2", "Hook + Ending", "Fast-paced montage")
- mood: Emotional vibe (e.g., "Calm / Inspirational", "Upbeat / High Energy")
- platform_popularity: Platform popularity note (e.g., "Viral on Instagram Reels & TikTok")
- royalty_free_alt: A royalty-free alternative song name (if creator needs commercial clearance)

Also provide list of 2-3 currently trending audio tags for:
- trending_instagram_audio
- trending_tiktok_audio
- trending_youtube_shorts_audio

{format_instructions}
"""

music_suggestion_prompt = PromptTemplate(
    template=MUSIC_SUGGESTION_TEMPLATE,
    input_variables=["idea", "tone", "audience", "language", "platform"],
    partial_variables={"format_instructions": ""}
)
