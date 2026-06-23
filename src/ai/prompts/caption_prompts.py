from langchain_core.prompts import PromptTemplate


caption_prompt = PromptTemplate(

template="""


You are an Instagram growth strategist.



Generate exactly 3 captions.



Script:

{script}



Tone:

{tone}



Audience:

{audience}



Requirements:


Short


Engaging


CTA


Emoji friendly





Return JSON.


Format



[
{{
"caption":""
}}
]




Only JSON.

No markdown.


""",



input_variables=[

"script",
"tone",
"audience"

]

)