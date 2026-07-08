import os
import urllib.request
import json

# Predefined few-shot examples corrected and verified by the user
FEW_SHOT_EXAMPLES = [
    {"english": "Make it shorter.", "gloss": "MAKE SHORT"},
    {"english": "One day, Akbar drew a line on the floor and ordered.", "gloss": "ONE DAY AKBAR DRAW LINE FLOOR ORDER"},
    {"english": "Make this line shorter.", "gloss": "THIS LINE MAKE SHORT"},
    {"english": "but don't rub out any part of it.", "gloss": "BUT RUB OUT NOT"},
    {"english": "No one knew what to do.", "gloss": "WHAT TO DO NO ONE KNOW"},
    {"english": "Each minister looked at the line and was puzzled.", "gloss": "EACH MINISTER LOOK LINE PUZZLE"},
    {"english": "No one could think of any way to make it longer.", "gloss": "MAKE LONG THINK NO ONE"},
    {"english": "No one could think of how it could be made shorter without erasing it.", "gloss": "ERASE NOT MAKE SHORT THINK NO ONE"},
    {"english": "What is your name?", "gloss": "YOUR NAME WHAT"},
    {"english": "I am going to school.", "gloss": "I SCHOOL GO"},
    {"english": "Today is a holiday.", "gloss": "TODAY HOLIDAY"},
    {"english": "My father is a teacher.", "gloss": "FATHER TEACHER"},
    {"english": "Where do you live?", "gloss": "YOU LIVE WHERE"},
    {"english": "He is a good boy.", "gloss": "HE BOY GOOD"},
    {"english": "I want to drink water.", "gloss": "I WATER DRINK WANT"},
    {"english": "We are playing cricket.", "gloss": "WE CRICKET PLAY"},
    {"english": "Who is calling me?", "gloss": "ME CALL WHO"},
    {"english": "Don't worry about it.", "gloss": "WORRY NOT"}
]

def get_ollama_model() -> str:
    """
    Queries local Ollama tags API to find the best qwen or llama model installed.
    """
    default_model = "qwen2.5-coder:7b"
    try:
        url = "http://localhost:11434/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = [m['name'] for m in data.get('models', [])]
            
            # Check if qwen2.5-coder:7b is explicitly present
            if default_model in models:
                return default_model
                
            # Otherwise look for any model containing 'qwen'
            for m in models:
                if 'qwen' in m.lower():
                    return m
            
            # Fallback to Llama or the first model
            for m in models:
                if 'llama' in m.lower():
                    return m
            
            if models:
                return models[0]
    except Exception as e:
        print(f"[Gloss] Warning: Could not reach Ollama API to list tags ({e}). Using default name '{default_model}'.")
    return default_model

def text_to_gloss(sentence: str, model_name: str = None) -> str:
    """
    Translates an English sentence into ISL Gloss representation.
    """
    if not model_name:
        model_name = get_ollama_model()
        
    url = "http://localhost:11434/api/generate"
    
    # Construct the instruction and few-shot examples
    system_instruction = (
        "You are an expert English to Indian Sign Language (ISL) translator.\n"
        "Your task is to convert the input English sentence into ISL Gloss representation.\n"
        "Rules:\n"
        "1. Prefer Subject-Object-Verb (SOV) order (e.g. 'I eat apple' -> 'I APPLE EAT').\n"
        "2. Drop helper verbs, articles, and prepositions (am, is, are, was, were, to, of, the, a, an).\n"
        "3. Plurals are indicated by repeating the word or adding 'MANY'.\n"
        "4. Negatives (NOT, NO, NEVER) go at the end of the clause.\n"
        "5. Question words (WHAT, WHY, WHEN, WHERE, WHO) go at the end.\n"
        "6. Output ONLY the uppercase gloss words, separated by spaces. Do NOT write explanations, quotes, or punctuation.\n\n"
        "Examples:\n"
    )
    
    for ex in FEW_SHOT_EXAMPLES:
        system_instruction += f"English: {ex['english']}\nISL Gloss: {ex['gloss']}\n\n"
        
    prompt = system_instruction + f"English: {sentence}\nISL Gloss:"
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for factual translation
            "stop": ["\n", "English:"]
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(payload).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            gloss = res_data.get('response', '').strip()
            
            # Clean up output: uppercase, strip trailing punctuation
            gloss = gloss.upper()
            gloss = "".join([c for c in gloss if c.isalnum() or c.isspace()])
            return " ".join(gloss.split())
    except Exception as e:
        print(f"[Gloss] Error during Ollama call: {e}")
        # Fallback to simple rule-based uppercase word extraction if Ollama is down
        words = [w.strip(".,?!\"'").upper() for w in sentence.split()]
        filtered = [w for w in words if w not in ('AM', 'IS', 'ARE', 'WAS', 'WERE', 'THE', 'A', 'AN', 'TO', 'OF')]
        return " ".join(filtered)

if __name__ == "__main__":
    # Test on 10 sample sentences
    test_sentences = [
        "What is your name?",
        "I am going to school.",
        "Today is a holiday.",
        "My father is a teacher.",
        "Where do you live?",
        "He is a good boy.",
        "I want to drink water.",
        "We are playing cricket.",
        "Who is calling me?",
        "Don't worry about it."
    ]
    
    model = get_ollama_model()
    print(f"Using model: {model}\n")
    print(f"{'English Sentence':<50} | {'ISL Gloss'}")
    print("-" * 80)
    for sent in test_sentences:
        gloss = text_to_gloss(sent, model)
        print(f"{sent:<50} | {gloss}")
    print("-" * 80)
