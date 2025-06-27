import numpy as np
import pandas as pd
from tqdm import tqdm
from datasets import Dataset
from transformers import pipeline
from sklearn.metrics import (accuracy_score,
                             classification_report,
                             confusion_matrix)
from sklearn.model_selection import train_test_split
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def generate_prompt(data_point):
    return f"""
            Read the problem and answer with TRUE or False.

            [{data_point["summary"]}] = {data_point["label"]}
            """.strip()

def generate_test_prompt(data_point):
    return f"""
            Read the problem and answer with TRUE or False.

            [{data_point["summary"]}] = """.strip()

def read_data():
    train_filename = "train_prompts.csv"
    test_filename = "test_prompts.csv"

    # Load CSVs
    x_train_full = pd.read_csv(train_filename, names=["label", "summary"], encoding="utf-8", encoding_errors="replace")
    x_test = pd.read_csv(test_filename, names=["label", "summary"], encoding="utf-8", encoding_errors="replace")

    # Sample 30 examples per label for evaluation from training set
    x_eval = (x_train_full
              .groupby("label", group_keys=False)
              .apply(lambda x: x.sample(n=30, random_state=10, replace=True)))

    # Remaining training data (excluding eval set)
    eval_indices = set(x_eval.index)
    x_train = x_train_full[~x_train_full.index.isin(eval_indices)]
    x_train = x_train.sample(frac=1, random_state=10).reset_index(drop=True)

    # Apply prompt generators
    x_train = pd.DataFrame(x_train.apply(generate_prompt, axis=1), columns=["text"])
    x_eval = pd.DataFrame(x_eval.apply(generate_prompt, axis=1), columns=["text"])
    y_true = x_test["label"]
    x_test = pd.DataFrame(x_test.apply(generate_test_prompt, axis=1), columns=["text"])

    # Convert to HuggingFace Datasets
    train_data = Dataset.from_pandas(x_train)
    eval_data = Dataset.from_pandas(x_eval)

    return train_data, eval_data, y_true, x_test


def evaluate(y_true, y_pred):
    mapping = {'true': 1, 'false': 0}

    def map_func(x):
        return mapping.get(x, 1)

    y_true = np.vectorize(map_func)(y_true)
    y_pred = np.vectorize(map_func)(y_pred)

    # Calculate accuracy
    accuracy = accuracy_score(y_true=y_true, y_pred=y_pred)
    print(f'Accuracy: {accuracy:.3f}')

    # Generate accuracy report
    unique_labels = set(y_true)  # Get unique labels

    for label in unique_labels:
        label_indices = [i for i in range(len(y_true))
                         if y_true[i] == label]
        label_y_true = [y_true[i] for i in label_indices]
        label_y_pred = [y_pred[i] for i in label_indices]
        accuracy = accuracy_score(label_y_true, label_y_pred)
        print(f'Accuracy for label {label}: {accuracy:.3f}')

    # Generate classification report
    class_report = classification_report(y_true=y_true, y_pred=y_pred)
    print('\nClassification Report:')
    print(class_report)

    # Generate confusion matrix
    conf_matrix = confusion_matrix(y_true=y_true, y_pred=y_pred, labels=[1, 0])
    print('\nConfusion Matrix:')
    print(conf_matrix)
    
def predict(test, model, tokenizer):
    y_pred = []
    pipe = pipeline(task="text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=1,
                    do_sample=True
                    )
    for i in tqdm(range(len(test))):
        prompt = test.iloc[i]["text"]
        result = pipe(prompt)
        answer = result[0]['generated_text'].split("=")[-1].lower()
        if "true" in answer:
            y_pred.append("true")
        else:
            y_pred.append("false")
    return y_pred

if __name__ == "__main__":
    read_data()