from src.ai.graph import graph


state = {

    "idea":"Morning routine",

    "goal":"Inspire",

    "tone":"Energetic",

    "style":"POV",

    "audience":"Students",

    "duration":15,

    "platform":"Instagram Reels",


    "hook":"",

    "scenes":[],

    "script":""

}


result = graph.invoke(state)


# print("\n")
# print("="*50)

# print("HOOK")
# print(result["hook"])

# print("="*50)

# print("SCENES")
# print(result["scenes"])


# print("="*50)

# print("SCRIPT")
# print(result["script"])

# print("="*50)

print(result["captions"])