import sys
import re
import string
import requests

FEW_SHOT_EXAMPLES = [
    ("Where do you live?", "YOU LIVE WHERE"),
    ("What is your name?", "YOUR NAME WHAT"),
    ("Today is a holiday.", "TODAY HOLIDAY"),
    ("I am going to the market.", "I MARKET TO GO"),
    ("My mother is cooking food.", "MY MOTHER FOOD COOK"),
    ("Why are you crying?", "YOU CRY WHY"),
    ("He is my brother.", "HE MY BROTHER"),
    ("I do not like coffee.", "I COFFEE LIKE NOT"),
    ("The book is on the table.", "BOOK TABLE ON"),
    ("I cannot come tomorrow.", "TOMORROW I COME CANNOT"),
    ("I want to eat an apple.", "I APPLE EAT WANT"),
    ("My dog is sleeping on the floor.", "MY DOG FLOOR ON SLEEP")
]

SYSTEM_PROMPT = """You are an expert translator from English to Indian Sign Language (ISL) Gloss.
Translate the input English sentence into ISL Gloss following these strict rules:
1. Translate to words/tokens in uppercase, stripped of punctuation.
2. WH-words (WHAT, WHERE, WHO, WHEN, WHY, HOW, WHICH) MUST always go at the very end of the sentence.
3. Copula/linking verbs (is, am, are, was, were, be, being, been) MUST always be dropped. Never include words like IS, AM, ARE, WAS, WERE, BE, BEEN in the output.
4. Always drop continuous/progressive aspect (-ing → base verb). For example, sleeping -> SLEEP, doing -> DO, walking -> WALK, laughing -> LAUGH, reading -> READ, speaking -> SPEAK.
5. Negation words (e.g. NOT, CANNOT, NEVER) MUST always go immediately after the verb or adjective they negate, never before. For example, "do not like" -> "LIKE NOT", "was not present" -> "PRESENT NOT".
6. Prepositions (e.g., ON, TO, IN, UNDER, FOR, WITH) become postpositions — the relevant noun/noun phrase comes first, the relation word after it. For example, "on the table" -> "TABLE ON", "to the market" -> "MARKET TO", "in the class" -> "CLASS IN", "with me" -> "ME WITH".
7. Retain modals and verbs expressing intent (e.g., CAN, MUST, SHOULD, WANT, WOULD) but place them after the verb they modify. For example, "can swim" -> "SWIM CAN", "must study" -> "STUDY MUST", "want to go" -> "GO WANT".
8. Time words (e.g., TODAY, TOMORROW, YESTERDAY, NOW) MUST always go at the very beginning of the sentence, before the subject.
9. Output ONLY the uppercase ISL gloss words separated by spaces. Do not write any explanations, notes, or punctuation.
"""

COPULAS = {"IS", "AM", "ARE", "WAS", "WERE", "BE", "BEING", "BEEN", "DOES", "DID"}
WH_WORDS = {"WHAT", "WHERE", "WHO", "WHEN", "WHY", "HOW", "WHICH"}
TIME_WORDS = {"TODAY", "TOMORROW", "YESTERDAY", "NOW"}
PREPOSITIONS = {"ON", "IN", "AT", "TO", "UNDER", "FOR", "WITH", "BY"}
MODALS = {"CAN", "MUST", "SHOULD", "WANT", "WOULD", "WILL", "COULD"}

def rule_based_gloss(text):
    """
    Algorithmic fallback for English -> ISL Gloss transformation.
    Applies ISL grammar rules directly without external LLM latency.
    """
    cleaned = text.translate(str.maketrans('', '', string.punctuation)).upper()
    words = cleaned.split()
    
    tokens = []
    time_tokens = []
    wh_tokens = []
    modal_tokens = []
    
    i = 0
    while i < len(words):
        w = words[i]
        if w in COPULAS:
            i += 1
            continue
            
        # Stem -ing suffix
        if len(w) > 4 and w.endswith("ING"):
            w = w[:-3]
            
        if w in TIME_WORDS:
            time_tokens.append(w)
        elif w in WH_WORDS:
            wh_tokens.append(w)
        elif w in MODALS:
            modal_tokens.append(w)
        elif w in PREPOSITIONS and tokens:
            # Postposition: swap with previous noun token
            prev = tokens.pop()
            tokens.append(prev)
            tokens.append(w)
        else:
            tokens.append(w)
        i += 1
        
    res = time_tokens + tokens + modal_tokens + wh_tokens
    return " ".join(res)

def clean_gloss(output):
    """
    Normalizes gloss text: converts to uppercase, removes punctuation, and strips extra spaces.
    Filters out remaining copulas as a safety net.
    """
    cleaned = output.strip().upper()
    cleaned = cleaned.translate(str.maketrans('', '', string.punctuation))
    words = cleaned.split()
    filtered_words = [w for w in words if w not in COPULAS]
    return " ".join(filtered_words)

def generate_gloss(english_text, model="qwen2.5-coder:7b"):
    """
    Translates an English sentence to ISL Gloss using local Ollama,
    with an instant rule-based ISL grammar fallback on timeout or error.
    """
    prompt = SYSTEM_PROMPT + "\n"
    for eng, gloss in FEW_SHOT_EXAMPLES:
        prompt += f"English: {eng}\nISL Gloss: {gloss}\n\n"
    prompt += f"English: {english_text}\nISL Gloss:"
    
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 40
        }
    }
    
    try:
        response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        raw_output = response.json().get("response", "")
        result = clean_gloss(raw_output)
        if result:
            return result
    except Exception:
        pass
        
    # Instant ISL rule-based fallback
    return rule_based_gloss(english_text)

if __name__ == "__main__":
    test_sentences = [
        "What are you doing tomorrow?",
        "My dog is sleeping on the floor.",
        "I want to go to the park.",
        "Why is she laughing?",
        "The weather is very nice today.",
        "Can you help me with this?",
        "Who will win the match?",
        "I am reading a very interesting book.",
        "He was not present in the class.",
        "Where did you buy this shirt?",
        "English these tips will make speaking"
    ]
    
    print("=== TESTING ISL GLOSS GENERATOR MODULE ===")
    for idx, sentence in enumerate(test_sentences, 1):
        gloss = generate_gloss(sentence)
        print(f"{idx:2d}. Input:  \"{sentence}\"")
        print(f"    Gloss:  {gloss}")
        print("-" * 50)

