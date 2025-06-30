import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from data_loading import read_data, predict, evaluate

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model_name = "meta-llama/Llama-3.2-3B"
adapter_path = "./trained_weights"
compute_dtype = torch.float16

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True,
)

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=compute_dtype,
    device_map=device,
)

# Load adapter onto base model
model = PeftModel.from_pretrained(
    base_model,
    adapter_path,
)

# Merge LoRA adapter into the base model weights
merged_model = model.merge_and_unload()

# Save merged model + tokenizer
merged_model.save_pretrained("merged_model", safe_serialization=True, max_shard_size="2GB")
tokenizer.save_pretrained("merged_model")

# Run your eval
_, _, y_true, x_test = read_data()
y_pred = predict(x_test, merged_model, tokenizer)
evaluate(y_true, y_pred)