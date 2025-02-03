import json
import requests
import time

# Prepare the API request
url = "http://137.132.92.202:4097/api/generate"

def generate_message(json_data: dict):
    messages = (
        "Please analyze the following Ethereum transaction for being exploit."
        "Transaction is stored in text form and we provide 3 detailed parts of transaction information."
        "First part is the basic information:"
        f"{json_data['transactionInfo']}"
        "Second part is the trace:"
        f"{json_data['trace']}"
        "Third part is the token changes of each address:"
        f"{json_data['balanceChanges']}"
        "Check for suspicious patterns and provide a risk assessment. Return a score between 0 - 100, with 60 indicates that it requires human checking."
    )

    return messages

def deepseekv3_detect(tx_hash, folder_prefix):
    # Read the content of the JSON file
    input_file = f"{folder_prefix}/output_{tx_hash}.json"
    output_file = f"{folder_prefix}/llm_result_{tx_hash}.txt"

    with open(input_file, "r") as json_file:
        json_data = json.load(json_file)

    messages = generate_message(json_data)
    payload = {
        "model": "nezahatkorkmaz/deepseek-v3:latest",
        "stream": False,
        "prompt": messages
    }

    start_time = time.time()  # Start time tracking

    # Send the request
    response = requests.post(url, json=payload)

    end_time = time.time()  # End time tracking
    elapsed_time = end_time - start_time  # Calculate elapsed time

    generated_text = response.json().get('response')

    print(generated_text)
    print(f"Response time: {elapsed_time:.2f} seconds")

    # Save output to a text file
    with open(output_file, "w", encoding="utf-8") as txt_file:
        txt_file.write(generated_text)

    return True
