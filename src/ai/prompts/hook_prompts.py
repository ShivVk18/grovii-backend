from langchain_core.prompts import PromptTemplate 





hook_prompt = PromptTemplate(

template="""
You are an elite creator strategist.


Generate ONLY ONE viral hook.


Requirements:

- under 15 words

- highly engaging

- scroll stopping

- match audience

- match tone




Idea:
{idea}



Goal:
{goal}



Tone:
{tone}




Audience:
{audience}



Platform:
{platform}




Return ONLY the hook.

""",


input_variables=[


'idea',

'goal',

'tone',

'audience',

'platform'

]


)