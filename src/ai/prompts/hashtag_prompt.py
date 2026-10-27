from langchain_core.prompts import PromptTemplate


hashtag_prompt = PromptTemplate(

template="""


You are an Instagram strategist.



Generate exactly 15 hashtags.



Script

{script}



Audience

{audience}




Return JSON


Format



[
{{

"hashtag":""

}}

]



Only JSON.



""",



input_variables=[

"script",

"audience"

]

)

# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

hashtag_prompt = harden(hashtag_prompt)
