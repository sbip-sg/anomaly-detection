import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from data_loading import read_data, predict, evaluate
import warnings
warnings.filterwarnings(action='ignore')
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def get_model():
    model_name = "meta-llama/Llama-3.2-3B"  # replace with actual HF model repo name

    compute_dtype = getattr(torch, "float16")

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map=device,  # or specify your device
        torch_dtype=compute_dtype,
        do_sample = False
    )

    model.config.use_cache = False
    model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return model, tokenizer

if __name__ == "__main__":
    _, _, y_true, x_test = read_data()
    model1, tokenizer1 = get_model()
    y_predict = predict(x_test, model1, tokenizer1)
    evaluate(y_true, y_predict)
