import json
from openai import OpenAI

# Set your API key
api_key = "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"

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
    client = OpenAI(
        api_key=api_key,
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )

    generated_text = response.choices[0].message.content

    print(generated_text)

    # Save output to a text file
    with open(output_file, "w", encoding="utf-8") as txt_file:
        txt_file.write(generated_text)

    return True
