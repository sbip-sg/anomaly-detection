import json
import os
from openai import OpenAI
import time

# Set your API key to environmental variable OPENAI_API_KEY

def generate_message(json_data: dict, few_shot_inputs = None):
    messages = [
        {
            "role": "system",
            "content": (
                "You are 'Sentinel', a highly skilled blockchain security analyst working in the Cyber Investigations Unit. "
                "Your task is to review blockchain transactions for potential exploits. "
                "You will be briefed with transaction data, traces, and balance changes, and you are expected to provide a professional risk assessment."
            )
        },
        {
            "role": "user",
            "content": "Sentinel, here is prior examples of normal transactions on same contract. Consider it as references."
        }]
    if few_shot_inputs:
        for example_input in few_shot_inputs:
            messages.extend(
            [{"role": "user", "content": "Example - Basic transaction information:"},
            {"role": "user", "content": example_input['transactionInfo']},
            {"role": "user", "content": "Example - Full trace of the transaction:"},
            {"role": "user", "content": example_input['trace']},
            {"role": "user", "content": "Example - Token balance changes:"},
            {"role": "user", "content": example_input['balanceChanges']}]
            )

    messages.extend([{
            "role": "user",
            "content": "Sentinel, we have an urgent case for you. Analyze the following EVM blockchain transaction and determine if it shows signs of being an exploit."
        },
        {"role": "user", "content": "First, here is the basic transaction information:"},
        {"role": "user", "content": json_data['transactionInfo']},
        {"role": "user", "content": "Next, this is the full trace of the transaction:"},
        {"role": "user", "content": json_data['trace']},
        {"role": "user", "content": "Finally, here are the token balance changes for the involved addresses:"},
        {"role": "user", "content": json_data['balanceChanges']},
        {
            "role": "user",
            "content": (
                "After your analysis, provide a risk score from 0 to 100. "
                "A score of 60 or above indicates that the transaction should be escalated for human review."
            )
        },
        {
            "role": "user",
            "content": (
                "Please respond **only with the risk score** in **JSON format** as follows: `{\"risk_score\": <number>}` "
                "Do not include any additional text, explanations, or formatting."
            )
        }
         ])

    return messages

def chatgpt_detect(tx_hash, folder_prefix, few_shot_learning):
    # Read the content of the JSON file
    input_file = f"{folder_prefix}/output_{tx_hash}.json"
    output_file = f"{folder_prefix}/llm_result_{tx_hash}.txt"
    with open(input_file, "r") as json_file:
        json_data = json.load(json_file)
    if few_shot_learning:
        few_shot_inputs = []
        input_folders = os.listdir(f"{folder_prefix}/few_shots")
        for example_hash in input_folders:
            example_file = f"{folder_prefix}/few_shots/{example_hash}/output_{example_hash}.json"
            with open(example_file, "r") as example_json_file:
                example_data = json.load(example_json_file)
            few_shot_inputs.append(example_data)
    else:
        few_shot_inputs = None

    messages = generate_message(json_data, few_shot_inputs)
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
