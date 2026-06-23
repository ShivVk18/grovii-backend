from langchain_core.prompts import PromptTemplate



script_prompt = PromptTemplate(

template="""

You are an expert short-form script writer.


Write a cohesive reel script.



Hook

{hook}




Scenes


{scenes}





Requirements


Natural


Conversational


Scroll stopping


Match tone


Audience:
{audience}



Platform:
{platform}



Return ONLY the script.



""",



input_variables=[


"hook",

"scenes",

"audience",

"platform"

]


)