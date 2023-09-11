from celery import shared_task
from celery import Task
import pandas as pd
import random, os
from flask import current_app, url_for
import json
from gptr.api_request_parallel_processor import process_api_requests_from_file
import asyncio
import logging

# NOTE: Heavy mental gymnastics here, have to refactor :)
api_key = "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"

@shared_task(ignore_result=False)
def generate_output(file, prompt, variables, form):
    df = pd.read_csv(file)

    jobs = []
    def generate_message(doc):
        message = prompt
        for v in variables:
            # name => first_name
            csv_key = form[v]
            message = message.replace("${" + v + "}", str(doc[csv_key]))
        
        return message

    for idx, row in df.iterrows():
        message = generate_message(row)
        
        jobs.append({"model": "gpt-3.5-turbo", "messages": [
                  {"role": "system", "content": message}
        ]})
            
    filename = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(f"{filepath}.jsonl", "w") as f:
        for job in jobs:
            json_string = json.dumps(job)
            f.write(json_string + "\n")

    save_filepath = f"{filepath}_results.jsonl"
    request_url = "https://api.openai.com/v1/chat/completions"
    print(save_filepath)
    asyncio.run(
        process_api_requests_from_file(
            requests_filepath=f"{filepath}.jsonl",
            save_filepath=save_filepath,
            request_url=request_url,
            api_key=api_key,
            max_requests_per_minute=float(3_000 * 0.5),
            max_tokens_per_minute=float(60_000),
            token_encoding_name="cl100k_base",
            max_attempts=int(5),
            logging_level=int(logging.INFO),
        )
    )

    with open(save_filepath, "r") as f:
        lines = f.readlines()

        new_data = []
        for idx, row in df.iterrows():
            message = generate_message(row)
            for line in lines:
                data = json.loads(line)
                input_message = data[0]["messages"][0]["content"]
                
                if message == input_message:
                    output_message = data[1]["choices"][0]["message"]["content"]
                    row['ouput'] = output_message
                    new_data.append(row)
                    break

            logging.warning("Cannot find the message")

    pd.DataFrame(new_data).to_csv(f"{filepath}_output.csv", index=False)
    return f"{filename}_output.csv"