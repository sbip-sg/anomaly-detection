from transformers import AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
from model_setup import get_model
from data_loading import read_data

# Load model + tokenizer
model, tokenizer = get_model()

# Load dataset
train_data, eval_data, _, _ = read_data()

def tokenize_fn(example):
    output = tokenizer(
        example["text"],
        truncation=True,
        padding="max_length",   # or "longest" / "do_not_pad" as needed
        max_length=512,
    )
    output["labels"] = output["input_ids"].copy()
    return output

train_data = train_data.map(tokenize_fn, batched=True, remove_columns=train_data.column_names)
eval_data = eval_data.map(tokenize_fn, batched=True, remove_columns=eval_data.column_names)

# Configure LoRA
peft_config = LoraConfig(
    r=4,
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules="all-linear",  # or better: ["q_proj", "v_proj"] depending on model
    bias="none",
    task_type="CAUSAL_LM",
)

# Apply LoRA to model
model = get_peft_model(model, peft_config)
model.gradient_checkpointing_enable()
model.enable_input_require_grads()


# Training args
training_args = TrainingArguments(
    output_dir="trained_weights",
    num_train_epochs=20,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    gradient_checkpointing=False,  # enable if large model / long sequence
    optim="adamw_torch_fused",     # preferred if using recent PyTorch
    save_strategy="epoch",
    logging_steps=1,
    learning_rate=5e-6,
    weight_decay=0.001,
    fp16=False,                    # try bf16 if your GPU supports
    max_grad_norm=0.3,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    report_to="none",              # or "wandb", "tensorboard" if you use them
)

# Set up trainer
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=eval_data
)

# Train
trainer.train()

# Save
trainer.save_model("trained_weights")
tokenizer.save_pretrained("trained_weights")