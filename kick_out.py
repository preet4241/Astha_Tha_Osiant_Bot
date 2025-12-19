# -*- coding: utf-8 -*-
import re
import json
import os
from fuzzywuzzy import fuzz

BAD_WORDS_FILE = 'bad_words.json'

DEFAULT_BAD_WORDS = [
    "madarchod", "mc", "bhosdike", "bsdk", "bhosdi", "bhosdiwale",
    "chutiya", "chutiye", "chu", "chtiya",
    "lodu", "lawde", "laude", "lund", "land",
    "gandu", "gaand", "gand",
    "randi", "raand", "rand",
    "harami", "haramkhor", "haraamzade",
    "maa ki", "teri maa", "maa chod", "maachod",
    "behen ki", "behenchod", "bc", "bhnchod",
    "sala", "saale", "kamina", "kamine",
    "kutte", "kutta", "suar", "suwar",
    "bakchod", "bakchodi",
    "jhant", "jhaat",
    "tatte", "tatti",
    "ullu", "gadha", "bevkoof", "bewakoof",
    "chirkut", "nalayak", "nikamma",
    "chhut", "chut",
    "teri behen", "behan ki",
    "maadar", "maadarchod",
    "bhadwa", "bhadwe",
    "hijra", "chakka",
    "fattu", "fatttoo"
]

def init_bad_words():
    if not os.path.exists(BAD_WORDS_FILE):
        save_bad_words(DEFAULT_BAD_WORDS)

def load_bad_words():
    init_bad_words()
    try:
        with open(BAD_WORDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return DEFAULT_BAD_WORDS

def save_bad_words(words):
    with open(BAD_WORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

def add_bad_words(new_words):
    current_words = load_bad_words()
    added = []
    for word in new_words:
        word = word.strip().lower()
        if word and word not in current_words:
            current_words.append(word)
            added.append(word)
    save_bad_words(current_words)
    return added

def remove_bad_words(words_to_remove):
    current_words = load_bad_words()
    removed = []
    for word in words_to_remove:
        word = word.strip().lower()
        if word in current_words:
            current_words.remove(word)
            removed.append(word)
    save_bad_words(current_words)
    return removed

def get_bad_words_count():
    return len(load_bad_words())

def get_bad_words_file_content():
    words = load_bad_words()
    content = "# Bad Words List\n"
    content += "# Total: {} words\n\n".format(len(words))
    for word in words:
        content += f"{word}\n"
    return content

def check_message_for_bad_words(text):
    """
    Check message for bad words using BOTH regex AND fuzzywuzzy matching.
    - Step 1: Regex matching for exact/word boundary matches (highest confidence)
    - Step 2: Fuzzy matching for typos and variations (medium-high confidence)
    """
    if not text:
        return False, []
    
    text_lower = text.lower()
    # Remove special characters but keep spaces
    text_clean = re.sub(r'[^a-zA-Z0-9\s]', '', text_lower)
    
    bad_words = load_bad_words()
    found_words = []
    
    # STEP 1: Regex matching (highest confidence)
    for word in bad_words:
        word_pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(word_pattern, text_clean):
            found_words.append(word)
            continue
        
        # Fallback: simple substring match if regex didn't work
        if word in text_clean:
            found_words.append(word)
    
    # STEP 2: Fuzzy matching for typos (only if no exact match found)
    if not found_words and len(text_clean.split()) <= 10:  # Max 10 words to check
        for word in bad_words:
            # Use token_set_ratio for better matching with word variations
            score = fuzz.token_set_ratio(text_clean, word)
            # Require 80% confidence for fuzzy match to avoid false positives
            if score >= 80:
                found_words.append(word)
    
    return len(found_words) > 0, found_words

def parse_bad_words_input(text):
    words = []
    lines = text.strip().split('\n')
    for line in lines:
        parts = re.split(r'[,;]', line)
        for part in parts:
            word = part.strip().lower()
            if word and not word.startswith('#'):
                words.append(word)
    return words
