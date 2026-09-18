from openrouter import OpenRouter
import os
from time import perf_counter

start_time = perf_counter()

with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
    response = client.chat.send(
        model="poolside/laguna-xs-2.1:free",
        # model="nvidia/nemotron-3.5-lightning:free",
        messages=[
            {"role": "user", "content": "What is the meaning of life?"}
        ],
    )

    print(response.choices[0].message.content)

print("elapsed Time: ", round(perf_counter() - start_time, 2))