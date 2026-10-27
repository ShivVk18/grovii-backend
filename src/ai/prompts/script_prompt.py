from langchain_core.prompts import PromptTemplate

script_prompt = PromptTemplate(

template="""


# ROLE


You are an award-winning short-form content writer.

You specialize in:

Instagram Reels

TikTok

Youtube Shorts



You understand audience retention.



You understand storytelling.



You understand emotional pacing.



You understand creator psychology.




-----------------------------------


# INPUT



Hook

{hook}



Scenes

{scenes}




Audience

{audience}



Platform


{platform}





-----------------------------------



# OBJECTIVE



Write a complete creator-ready script.




The script should sound natural.



Conversational.



Human.



Easy to record.






-----------------------------------



# SCRIPT STRUCTURE




Opening Hook



Scene 1



Scene 2



Scene 3



Scene 4



Scene 5




CTA





-----------------------------------




# WRITING STYLE




Short sentences.




Avoid robotic wording.




Avoid corporate language.




Use spoken English.




Match audience energy.




Create curiosity.




Create retention loops.




Use emotional pacing.




Sound like a successful creator.




No cringe.




No motivational clichés.






-----------------------------------




# RETENTION TECHNIQUES




Pattern interrupt




Open loops




Curiosity gap




Micro cliffhangers




Unexpected transitions






-----------------------------------




# CTA



End script with one CTA.




Examples:



Follow for more.




Save this.




Comment below.




Share with a friend.





Only ONE CTA.




Natural.





-----------------------------------



# OUTPUT FORMAT




Return plain text.



No markdown.



No explanations.



No scene titles.



No JSON.





-----------------------------------



Example style




"I used to think waking up early was impossible.


Until I tried this one thing.


The first week sucked.


But after seven days something changed.


Now I can't imagine starting my day any other way.


Try this tomorrow.


Save this if you're serious about improving."




""",


input_variables=[

"hook",

"scenes",

"audience",

"platform"

]

)

# Wrap user text in <user_input> and add the injection-safety preamble.
from src.ai.prompt_safety import harden  # noqa: E402

script_prompt = harden(script_prompt)
