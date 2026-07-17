import sys
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
    ("When will you come?", "YOU COME WHEN"),
    ("This apple is sweet.", "THIS APPLE SWEET"),
    ("Who is that person?", "THAT PERSON WHO"),
    ("I do not like coffee.", "I COFFEE LIKE NOT"),
    ("Are you happy?", "YOU HAPPY"),
    ("How did you do that?", "YOU THAT DO HOW"),
    ("She was dancing yesterday.", "YESTERDAY SHE DANCE"),
    ("I have two dogs.", "I DOG TWO HAVE"),
    ("Is it raining?", "RAIN"),
    ("Please give me some water.", "PLEASE WATER GIVE ME"),
    ("We are learning sign language.", "WE SIGN LANGUAGE LEARN"),
    ("The book is on the table.", "BOOK TABLE ON"),
    ("I cannot come tomorrow.", "TOMORROW I COME CANNOT"),
    ("Where is the bathroom?", "BATHROOM WHERE"),
    ("Which book do you want?", "YOU BOOK WANT WHICH"),
    ("I am tired.", "I TIRED"),
    ("He is driving a car.", "HE CAR DRIVE"),
    ("They are playing football.", "THEY FOOTBALL PLAY"),
    ("He was not present in the class.", "HE CLASS IN PRESENT NOT"),
    ("I can swim.", "I SWIM CAN"),
    ("You must study.", "YOU STUDY MUST"),
    ("Can you play with me?", "YOU ME WITH PLAY CAN"),
    ("I want to eat an apple.", "I APPLE EAT WANT"),
    ("My cat is sleeping on the bed.", "MY CAT BED ON SLEEP")
]

SYSTEM_PROMPT = """You are an expert translator from English to Indian Sign Language (ISL) Gloss.
Translate the input English sentence into ISL Gloss following these strict rules:
1. Translate to words/tokens in uppercase, stripped of punctuation.
2. WH-words (WHAT, WHERE, WHO, WHEN, WHY, HOW, WHICH) MUST always go at the very end of the sentence.
3. Copula/linking verbs (is, am, are, was, were, be, being, been) MUST always be dropped. Never include words like IS, AM, ARE, WAS, WERE, BE, BEEN in the output.
4. Always drop continuous/progressive aspect (-ing → base verb). For example, sleeping -> SLEEP, doing -> DO, walking -> WALK, laughing -> LAUGH, reading -> READ.
5. Negation words (e.g. NOT, CANNOT, NEVER) MUST always go immediately after the verb or adjective they negate, never before. For example, "do not like" -> "LIKE NOT", "was not present" -> "PRESENT NOT".
6. Prepositions (e.g., ON, TO, IN, UNDER, FOR, WITH) become postpositions — the relevant noun/noun phrase comes first, the relation word after it. For example, "on the table" -> "TABLE ON", "to the market" -> "MARKET TO", "in the class" -> "CLASS IN", "with me" -> "ME WITH", "with this" -> "THIS WITH", "on the floor" -> "FLOOR ON".
7. Retain modals and verbs expressing intent (e.g., CAN, MUST, SHOULD, WANT, WOULD) but place them after the verb they modify. For example, "can swim" -> "SWIM CAN", "must study" -> "STUDY MUST", "want to go" -> "GO WANT", "can help" -> "HELP CAN".
8. Time words (e.g., TODAY, TOMORROW, YESTERDAY, NOW) MUST always go at the very beginning of the sentence, before the subject. For example, "What are you doing tomorrow?" -> "TOMORROW YOU DO WHAT", "The weather is very nice today." -> "TODAY WEATHER VERY NICE".
9. Output ONLY the uppercase ISL gloss words separated by spaces. Do not write any explanations, notes, or punctuation.

Here are examples of correct translations:
"""

def clean_gloss(output):
    """
    Normalizes gloss text: converts to uppercase, removes punctuation, and strips extra spaces.
    Additionally, filters out any remaining copulas that the model might have incorrectly included.
    """
    cleaned = output.strip().upper()
    # Remove punctuation except spaces
    punctuation_to_remove = string.punctuation
    cleaned = cleaned.translate(str.maketrans('', '', punctuation_to_remove))
    # Replace multiple spaces/newlines with a single space
    words = cleaned.split()
    # Post-filtering copulas as a safety net
    copulas = {"IS", "AM", "ARE", "WAS", "WERE", "BE", "BEING", "BEEN"}
    filtered_words = [w for w in words if w not in copulas]
    return " ".join(filtered_words)

def generate_gloss(english_text, model="qwen2.5-coder:7b"):
    """
    Translates an English sentence to ISL Gloss using local Ollama.
    """
    # Build the few-shot prompt
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
        }
    }
    
    try:
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        raw_output = response.json().get("response", "")
        return clean_gloss(raw_output)
    except Exception as e:
        raise Exception(f"Failed to query local Ollama: {str(e)}")

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
        "Where did you buy this shirt?"
    ]
    
    print("=== TESTING ENGLISH TO ISL GLOSS MODULE (REFINED RULES V4) ===")
    print("Sending prompts to local Ollama (qwen2.5-coder:7b)...")
    
    success = True
    for idx, sentence in enumerate(test_sentences, 1):
        try:
            gloss = generate_gloss(sentence)
            print(f"{idx}. Input:  \"{sentence}\"")
            print(f"   Gloss:  {gloss}")
            print("-" * 50)
        except Exception as e:
            print(f"{idx}. Input:  \"{sentence}\"")
            print(f"   Error:  {e}")
            print("-" * 50)
            success = False
            
    if not success:
        sys.exit(1)
