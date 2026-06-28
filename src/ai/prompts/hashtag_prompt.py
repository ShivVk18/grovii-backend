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