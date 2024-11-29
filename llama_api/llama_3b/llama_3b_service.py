# llama_3b_service.py

from transformers import pipeline

def generate_text(prompt, max_new_tokens=400):

    messages = [
        {"role": "user", "content": prompt},
    ]
    pipe = pipeline("text-generation", model="meta-llama/Llama-3.2-1B-Instruct")
    output = pipe(messages,max_new_tokens=max_new_tokens)
    generated_text = output[0]['generated_text']
    print(generated_text)
    return generated_text
