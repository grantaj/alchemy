import ollama

def filter_text(input_text):
    prompt = f"""
    Rewrite the following text to:
    - Remove clickbait and sensationalism.
    - Summarize in plain English.
    - Identify any bias or subjective language.

    Original Text: "{input_text}"

    Output:
    """

    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]

# Example usage
text = "Shocking discovery! You won't believe what this new study reveals about coffee!"
filtered_text = filter_text(text)
print("Filtered Output:\n", filtered_text)
