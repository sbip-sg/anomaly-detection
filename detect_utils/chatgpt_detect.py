import json
from openai import OpenAI
import time

# Set your API key to environmental variable OPENAI_API_KEY

def generate_message(json_data: dict):
    messages = [
        {"role": "user", "content": "Please analyze the following Ethereum transaction for being exploit."},
        {"role": "user",
         "content": "Transaction is stored in text form and we provide 3 detailed parts of transaction information."},
        {"role": "user", "content": "First part is the basic information:"},
        {"role": "user", "content": json_data['transactionInfo']},
        {"role": "user", "content": "Second part is the trace:"},
        {"role": "user", "content": json_data['trace']},
        {"role": "user", "content": "Third part is the token changes of each address:"},
        {"role": "user", "content": json_data['balanceChanges']},
        {"role": "user",
         "content": "Check for suspicious patterns and provide a risk assessment. Return a score between 0 - 100, with 60 indicates that it requires human checking."},
    ]

    return messages

def chatgpt_detect(tx_hash, folder_prefix):
    # Read the content of the JSON file
    input_file = f"{folder_prefix}/output_{tx_hash}.json"
    output_file = f"{folder_prefix}/llm_result_{tx_hash}.txt"

    with open(input_file, "r") as json_file:
        json_data = json.load(json_file)

    messages = generate_message(json_data)
    client = OpenAI()

    start_time = time.time()  # Start time tracking

    response = client.chat.completions.create(
        model="o3-mini",
        messages=messages
    )

    end_time = time.time()  # End time tracking
    elapsed_time = end_time - start_time  # Calculate elapsed time

    generated_text = response.choices[0].message.content

    print(generated_text)
    print(f"Response time: {elapsed_time:.2f} seconds")

    # Save output to a text file
    with open(output_file, "w", encoding="utf-8") as txt_file:
        txt_file.write(generated_text)

    return True
