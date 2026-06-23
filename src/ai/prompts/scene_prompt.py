from langchain_core.prompts import PromptTemplate


scene_prompt = PromptTemplate(

template="""

You are an elite storyboard creator.

Generate exactly 5 scenes.



Idea:
{idea}


Hook:
{hook}


Tone:
{tone}


Audience:
{audience}



Return ONLY valid JSON.


Format:


[
{{
"title":"",
"description":"",
"visual_cue":"",
"script_segment":""
}}
]



No markdown.

No explanation.



""",



input_variables=[

'idea',
'hook',
'tone',
'audience'

]

)