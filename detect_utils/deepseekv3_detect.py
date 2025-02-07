import json
import requests
import time

# Prepare the API request
url = "http://137.132.92.202:4097/api/generate"


def generate_message(json_data: dict):
    messages = (
        "You are an advanced Ethereum transaction security analyst. Your task is to analyze the following Ethereum transaction for potential exploits, suspicious behaviors, or attack patterns. "
        "The transaction is broken down into three detailed sections:\n\n"

        "1️⃣ **Basic Information:**\n"
        f"{json_data['transactionInfo']}\n\n"

        "2️⃣ **Execution Trace:**\n"
        f"{json_data['trace']}\n\n"

        "3️⃣ **Token Balance Changes:**\n"
        f"{json_data['balanceChanges']}\n\n"

        "### **Analysis Instructions:**\n"
        "- Look for common exploit patterns such as reentrancy attacks, sandwich attacks, price manipulation, flash loan exploits, or MEV-related behaviors.\n"
        "- Identify unusual contract interactions, self-destruct mechanisms, or unexpected gas usage.\n"
        "- Assess whether token movements indicate potential wash trading or money laundering.\n\n"

        "### **Risk Assessment Criteria:**\n"
        "Provide a risk score between **0 and 100** based on your analysis:\n"
        "- **0-30:** Low risk, likely a normal transaction.\n"
        "- **31-59:** Medium risk, possible anomalies but no strong exploit indicators.\n"
        "- **60-100:** High risk, requires human review due to strong exploit signs.\n\n"

        "### **Expected Response Format:**\n"
        "Return your assessment in the following structured format:\n"
        "```\n"
        "{\n"
        '  "risk_score": 75,\n'
        '  "verdict": "Potential exploit detected due to reentrancy attack",\n'
        '  "reasoning": "The trace indicates multiple reentrant calls within the same transaction.",\n'
        '  "recommendation": "Further manual review is advised. Consider blocking associated addresses."\n'
        "}\n"
        "```\n"
        "Now, please analyze the transaction and return your findings."
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
        "prompt": messages,
        "options": {
            "num_ctx": 70000
        }
    }

    start_time = time.time()  # Start time tracking

    # Send the request
    response = requests.post(url, json=payload)

    end_time = time.time()  # End time tracking
    elapsed_time = end_time - start_time  # Calculate elapsed time

    generated_text = response.json().get('response')
    print(f"Response time: {elapsed_time:.2f} seconds")

    # Save output to a text file
    with open(output_file, "w", encoding="utf-8") as txt_file:
        txt_file.write(generated_text)

    return True
