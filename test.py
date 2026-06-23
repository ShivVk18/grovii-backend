# from src.services.openai_service import openai_service 

# llm = openai_service.get_llm() 


# response = llm.invoke(
#     "Say hello"
# )

# print(response.content)


from src.ai.prompts.hook_prompts import hook_prompt


prompt = hook_prompt.format(


idea="Morning routine",


goal="Inspire",


tone="Energetic",


audience="Students",


platform="Instagram Reels"

)



print(prompt)