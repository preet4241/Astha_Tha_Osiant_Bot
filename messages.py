# -*- coding: utf-8 -*-
import random
import re
from fuzzywuzzy import fuzz

HELLO_MESSAGES = [
    "👋 Namaste {name}! Kaise ho bhai? Umeed hai sab badhiya chal raha hai! 😊",
    "🙏 Hello {name}! Aaj ka din shubh ho tumhara! Maze karo! 🌟",
    "👋 Hey {name}! Kya haal chaal hai? Bot ready hai tumhari seva mein! 🤖",
    "🌞 Suprabhat {name}! Aaj ka din aapka ho ekdum awesome! ✨",
    "😎 Yo {name}! What's up bhai? Sab theek thaak? 👍",
    "🎉 Welcome {name}! Bahut khushi hui tumse milke! 💫",
    "👋 Hi {name}! Kaisa chal raha hai aaj? Hope you're doing great! 🌈",
    "🙌 Hello ji {name}! Aap aaye bahar aayi! Welcome welcome! 🎊",
    "😊 Namaskaar {name}! Aaj ka din mangalmay ho aapka! 🕉️",
    "🌟 Hey there {name}! Ready for some action? Let's go! 🚀",
    "👋 Aadaab {name}! Kaise mizaaj hain aaj? 🌹",
    "🎭 Hello {name}! Life mein thoda drama chahiye? Main hoon na! 😄",
    "🌺 Pranam {name}! Aapka din shubh aur mangalmay ho! 🙏",
    "😃 Hi {name}! Aaj mood kaisa hai? Hopefully fantastic! 🎈",
    "🤗 Hello {name}! Ek bada wala virtual hug lo! 🤗",
    "⭐ Hey {name}! Tum toh star ho yaar! Shine on! ✨",
    "🎵 Hello {name}! Aaj kuch toofani karte hain! 🌪️",
    "🌻 Hi {name}! Sunflower ki tarah khilte raho hamesha! 🌻",
    "🦋 Namaste {name}! Life mein colors bhari ho! 🌈",
    "🎪 Welcome {name}! Ab party shuru ho gayi! 🎉",
    "🌙 Hello {name}! Chaand sa chamakta chehra hai tumhara! 🌟",
    "🎯 Hey {name}! Aaj targets sabhi hit karenge! 🎯",
    "🏆 Hi {name}! Winner toh tum ho already! 🥇",
    "🔥 Yo {name}! Aag laga di tumne toh! Full fire! 🔥",
    "💪 Hello {name}! Stay strong, stay blessed! 💫",
    "🌊 Hi {name}! Chill vibes only aaj! 🏖️",
    "🎸 Hey {name}! Rock on bhai! 🤘",
    "🌴 Namaste {name}! Life is beautiful, enjoy karo! 🌺",
    "🎨 Hello {name}! Aaj kuch creative karo! 🖌️",
    "📚 Hi {name}! Knowledge is power! Keep learning! 💡",
    "🚀 Hey {name}! To the moon and beyond! 🌙",
    "💎 Hello {name}! Tum diamond ho bhai! Rare and precious! 💎",
    "🌈 Namaste {name}! Har din ek naya rang lao! 🎨",
    "🎁 Hi {name}! Life is a gift, unwrap it daily! 🎀",
    "🌟 Hello {name}! Tumhari star quality ekdum jhakkas hai! ⭐",
    "🎵 Hey {name}! Zindagi ek gaana hai, gaate raho! 🎶",
    "🦅 Hi {name}! Ooncha udo, dur dekho! Fly high! 🚀",
    "🌻 Hello {name}! Positive vibes only! 😊",
    "🎭 Namaste {name}! Drama kam, karma zyada! 😄",
    "🏆 Hey {name}! Champions ki tarah jiyo! 🥇",
    "🌊 Hi {name}! Go with the flow bhai! 🌴",
    "💫 Hello {name}! Magic happens when you believe! ✨",
    "🎪 Hey {name}! Life is a circus, enjoy the show! 🎠",
    "🦋 Namaste {name}! Transform karo, grow karo! 🌱",
    "🎯 Hi {name}! Focused rehna, success milega! 🎯",
    "🌙 Hello {name}! Sweet dreams and better realities! 🌟",
    "🔥 Hey {name}! Passion se karo, result best aayega! 💪",
    "🎸 Namaste {name}! Apni dhun pe nachte raho! 🎵",
    "💎 Hi {name}! Polish karo khud ko daily! Shine bright! ✨",
    "🌈 Hello {name}! After every storm comes a rainbow! 🌧️",
    "🎁 Hey {name}! Appreciate the small things! 🌺",
    "🚀 Namaste {name}! Impossible se mumkin tak! Let's go! 💪",
    "🌟 Hi {name}! Tum wahi ho jo duniya badal sakta hai! 🌍",
    "🎵 Hello {name}! Apni zindagi ka DJ khud bano! 🎧",
    "🦅 Hey {name}! Limits sirf dimaag mein hoti hain! Break them! 💥",
    "🌻 Namaste {name}! Har subah ek naya mauka hai! 🌅",
    "🎭 Hi {name}! Be the hero of your own story! 🦸",
    "🏆 Hello {name}! Success ka raasta aapke paas se guzarta hai! 🛤️",
    "🌊 Hey {name}! Stay calm like water, powerful like storm! ⛈️",
    "💫 Namaste {name}! Universe tumhare saath hai! 🌌",
    "🎪 Hi {name}! Laugh more, worry less! 😂",
    "🦋 Hello {name}! Change is beautiful, embrace it! 🤗",
    "🎯 Hey {name}! Eyes on the prize, always! 👀",
    "🌙 Namaste {name}! Dream big, work hard! 💪",
    "🔥 Hi {name}! Passion + Patience = Success! 🏆",
    "🎸 Hello {name}! Make some noise! 📢",
    "💎 Hey {name}! Value yourself, others will follow! 👑",
    "🌈 Namaste {name}! Spread colors of happiness! 🎨",
    "🎁 Hi {name}! Every moment is precious! ⏰",
    "🚀 Hello {name}! Sky is not the limit, it's just the beginning! 🌌",
    "🌟 Hey {name}! Aaj ka hero tum ho! 🦸‍♂️",
    "🎵 Namaste {name}! Life ka music never stops! 🎶",
    "🦅 Hi {name}! Soar high, roar loud! 🦁",
    "🌻 Hello {name}! Be the sunshine in someone's life! ☀️",
    "🎭 Hey {name}! Life is short, make it sweet! 🍬",
    "🏆 Namaste {name}! Born to win! 🥇",
    "🌊 Hi {name}! Keep flowing, keep growing! 🌱",
    "💫 Hello {name}! Believe in yourself! You're amazing! 🌟",
    "🎪 Hey {name}! Fun times ahead! Get ready! 🎢",
    "🦋 Namaste {name}! Transformation ka time hai! 🔄"
]

GOOD_MORNING_MESSAGES = [
    "🌅 Good morning {name}! Aaj ka din zabardast ho! ☀️",
    "🌞 Suprabhat {name}! Subah ki taza hawa lo! 🌸",
    "☀️ Good morning bhai {name}! Rise and shine! 🌟",
    "🌄 Subah ho gayi mamu {name}! Uth jao! 😄",
    "🌅 GM {name}! Aaj ka din tera hai, rock it! 🎸",
    "🌞 Subah ki chai ho ya coffee, din shuru karo {name}! ☕",
    "☀️ Good morning {name}! Nayi subah, naye mauke! 🚀",
    "🌄 Suprabhat {name}! Har subah ek nayi shuruaat hai! 🌈",
    "🌅 GM {name}! Subah se hi positive vibes! ✨",
    "🌞 Good morning {name}! Aaj ka din aapka hai! 🏆",
    "☀️ Subah ho gayi {name}! Time to hustle! 💪",
    "🌄 Good morning bhai! Neend puri hui {name}? 😴",
    "🌅 GM {name}! Coffee pi aur duniya jeet! ☕🏆",
    "🌞 Suprabhat {name}! Subah ki kirno se bhari ho zindagi! 🌸",
    "☀️ Good morning {name}! Let's make today count! 📈"
]

GOOD_NIGHT_MESSAGES = [
    "🌙 Good night {name}! Meethe sapne dekho! 💤",
    "✨ Shubh ratri {name}! Kal phir milenge! 🌟",
    "🌙 GN {name}! Neend achi aaye bhai! 😴",
    "💤 Good night {name}! Rest karo, kal phir josh mein! 💪",
    "🌟 Shubh ratri {name}! Sweet dreams! 🌈",
    "🌙 Good night bhai {name}! Kal naya din, naye mauke! ☀️",
    "✨ GN {name}! Thak gaye ho, rest lo! 🛏️",
    "💤 Shubh ratri {name}! Kal phir dhoom machayenge! 🎉",
    "🌙 Good night {name}! Stars tumpe meherbaan! ⭐",
    "🌟 GN {name}! Peaceful sleep bhai! 🕊️"
]

GOOD_AFTERNOON_MESSAGES = [
    "☀️ Good afternoon {name}! Lunch ka time hai! 🍽️",
    "🌞 Subh dopahar {name}! Energy level up karo! ⚡",
    "☀️ Afternoon vibes {name}! Half day done! 💪",
    "🌞 Good afternoon bhai {name}! Chal kaise chal raha din? 😊",
    "☀️ Dopahar ho gayi {name}! Rest le lo thoda! 😌",
    "🌞 GA {name}! Keep grinding! 🔥",
    "☀️ Good afternoon {name}! Productivity mode on! 🚀",
    "🌞 Subh dopahar {name}! Thoda break le lo! ☕"
]

GOOD_EVENING_MESSAGES = [
    "🌆 Good evening {name}! Din kaisa gaya? 😊",
    "🌅 Shubh sandhya {name}! Relax karo ab! 🧘",
    "🌆 GE {name}! Evening walk pe chalo! 🚶",
    "🌅 Good evening bhai {name}! Sunset enjoy karo! 🌇",
    "🌆 Shubh sandhya {name}! Kal ke liye ready? 💪",
    "🌅 Good evening {name}! Family time enjoy karo! 👨‍👩‍👧",
    "🌆 GE {name}! Din ki thakaan utar gayi? 😌",
    "🌅 Shubh sandhya {name}! Chai pi lo! ☕"
]

GREETING_RESPONSES = [
    "👋 Haan bhai {name}! Bol kya haal hai? 😊",
    "🙏 Haan {name}! Batao kya kar rahe ho? 🤔",
    "👋 Hello {name}! Kaise ho yaar? 😄",
    "🙌 Kya baat hai {name}! Aaj kaisa din chal raha? 🌟",
    "👋 Haanji {name}! Bolo bolo! 😎",
    "🙏 Namaste {name}! Sab badhiya? 🌸",
    "👋 Hey {name}! What's up bro? 🤙",
    "🙌 Yo {name}! Kya scene hai aaj? 🔥",
    "👋 Hii {name}! Missed you yaar! 🤗",
    "🙏 Hello {name}! Long time no see! 👀",
    "👋 Kya haal {name}? Sab theek? 💯",
    "🙌 Bolo bhai {name}! Kaise ho? 😊",
    "👋 Arey {name}! Kahan the itne din? 🤷",
    "🙏 Haan bhai {name}! Batao kya help chahiye? 🛠️",
    "👋 Wassup {name}! All good? 👍"
]

HOW_ARE_YOU_RESPONSES = [
    "😊 Main ekdum mast {name}! Tum batao? 🌟",
    "💪 Badiya bhai {name}! Aur tumhara kya haal? 😄",
    "🌟 Zabardast {name}! Tumhari seva mein hazir! 🤖",
    "😎 Full power pe hoon {name}! Tum kaise ho? 🔥",
    "👍 Sab badhiya {name}! Bolo kya kar sakte hain? 😊",
    "🙏 Theek hoon {name}! Aur aap? 🌸",
    "💯 First class {name}! Aur batao? 🎉",
    "😄 Ekdum fit {name}! Tumhari health kaisi? 💪",
    "🌈 Mast {name}! Zindagi jhingalala! 🎵",
    "👋 Chal raha hai {name}! Aur tum? 😊"
]

THANK_YOU_RESPONSES = [
    "🙏 Welcome {name}! Koi baat nahi! 😊",
    "😊 Mention not {name}! Kabhi bhi help karo! 🤝",
    "🌟 No problem {name}! Always here for you! 💪",
    "👍 Pleasure {name}! Har waqt ready! 🔥",
    "🙏 Dhanyawad {name}! Tum bhi mast ho! 😄",
    "😊 Welcome bhai {name}! Apna samjho! 🤗",
    "🌸 Koi nahi {name}! Yeh toh hamara farz hai! 🙏",
    "💯 Always {name}! Bolo aur kya chahiye? 😊"
]

BYE_RESPONSES = [
    "👋 Bye {name}! Phir milenge! 😊",
    "🙏 Alvida {name}! Take care! 🌟",
    "👋 Bye bye {name}! Miss karenge! 🤗",
    "🌟 Chal phir {name}! Jaldi aana! 😄",
    "👋 TC {name}! See you soon! 👍",
    "🙏 Bye {name}! Khush raho! 🌸",
    "👋 Phir milenge {name}! Take it easy! 😎",
    "🌟 Bye bhai {name}! Apna khayal rakhna! 💪"
]

LAUGH_RESPONSES = [
    "😂 Haha {name}! Mast joke tha! 🤣",
    "🤣 Lol {name}! Hassi aa gayi! 😆",
    "😄 Hehe {name}! Mazak mein mast ho! 🎭",
    "😂 Bhai {name}! Comedy king ho tum! 👑",
    "🤣 Hahaha {name}! Pet dukh gaya hasste hasste! 😆",
    "😄 Nice one {name}! Keep the humor coming! 🎪",
    "😂 Wahh {name}! Dil khush kar diya! 💖",
    "🤣 Mast tha {name}! Aur sunao! 😄"
]

SAD_RESPONSES = [
    "🤗 Koi nahi {name}! Sab theek ho jayega! 💪",
    "❤️ Don't worry {name}! Main hoon na! 🤝",
    "🌟 Himmat mat haro {name}! Kal acha hoga! ☀️",
    "🤗 Tension mat lo {name}! Ye waqt bhi guzar jayega! 🌈",
    "❤️ Stay strong {name}! You've got this! 💪",
    "🌟 Udas mat ho {name}! Life bahut badi hai! 🌍",
    "🤗 Cheer up {name}! Smile karo! 😊",
    "❤️ Sab badhiya hoga {name}! Believe it! ✨"
]

GREETING_KEYWORDS = {
    'hello': ['hello', 'hellow', 'helo', 'hlo', 'hellw', 'helloo'],
    'hi': ['hi', 'hii', 'hiii', 'hiiii', 'hiiiii', 'hy', 'hyyy', 'hyy'],
    'hey': ['hey', 'heyy', 'heyyy', 'hay', 'hayy', 'hayyy'],
    'good_morning': ['good morning', 'goodmorning', 'gm', 'gud morning', 'gud mrng', 'good mrng', 'subah', 'suprabhat', 'g morning', 'morning'],
    'good_night': ['good night', 'goodnight', 'gn', 'gud night', 'gud nyt', 'nyt', 'shubh ratri', 'night'],
    'good_afternoon': ['good afternoon', 'goodafternoon', 'ga', 'gud afternoon', 'dopahar'],
    'good_evening': ['good evening', 'goodevening', 'ge', 'gud evening', 'shubh sandhya', 'evening'],
    'how_are_you': ['how are you', 'kaise ho', 'kaisa hai', 'kaisi ho', 'how r u', 'hru', 'kya haal', 'kya hal', 'haal chaal', 'sab theek', 'sab thik', 'how you doing', 'howdy', 'sup'],
    'thank_you': ['thank you', 'thankyou', 'thanks', 'thnx', 'thx', 'shukriya', 'dhanyawad', 'ty', 'tysm'],
    'bye': ['bye', 'byee', 'byeee', 'goodbye', 'good bye', 'alvida', 'chal phir', 'tc', 'take care', 'see you', 'later', 'gtg'],
    'laugh': ['haha', 'hahaha', 'lol', 'lmao', 'rofl', 'hehe', 'hehehe', 'xd', '😂', '🤣', '😆'],
    'sad': ['sad', 'udas', 'dukhi', 'tension', 'stressed', 'pareshan', '😢', '😭', '😔', '🥺']
}

def get_random_hello_message(name: str) -> str:
    message = random.choice(HELLO_MESSAGES)
    return message.format(name=name)

def get_random_greeting_response(name: str) -> str:
    message = random.choice(GREETING_RESPONSES)
    return message.format(name=name)

def get_random_good_morning_message(name: str) -> str:
    message = random.choice(GOOD_MORNING_MESSAGES)
    return message.format(name=name)

def get_random_good_night_message(name: str) -> str:
    message = random.choice(GOOD_NIGHT_MESSAGES)
    return message.format(name=name)

def get_random_good_afternoon_message(name: str) -> str:
    message = random.choice(GOOD_AFTERNOON_MESSAGES)
    return message.format(name=name)

def get_random_good_evening_message(name: str) -> str:
    message = random.choice(GOOD_EVENING_MESSAGES)
    return message.format(name=name)

def get_random_how_are_you_response(name: str) -> str:
    message = random.choice(HOW_ARE_YOU_RESPONSES)
    return message.format(name=name)

def get_random_thank_you_response(name: str) -> str:
    message = random.choice(THANK_YOU_RESPONSES)
    return message.format(name=name)

def get_random_bye_response(name: str) -> str:
    message = random.choice(BYE_RESPONSES)
    return message.format(name=name)

def get_random_laugh_response(name: str) -> str:
    message = random.choice(LAUGH_RESPONSES)
    return message.format(name=name)

def get_random_sad_response(name: str) -> str:
    message = random.choice(SAD_RESPONSES)
    return message.format(name=name)

def detect_greeting_type(text: str) -> str:
    """
    Detect greeting type using BOTH regex AND fuzzywuzzy matching.
    - First tries exact/regex matching (high precision)
    - Then uses fuzzy matching for typos/variations (high recall)
    - Returns greeting type only if confidence is high enough
    """
    text_lower = text.lower().strip()
    
    # STEP 1: Try regex matching for exact/word boundary matches (highest confidence)
    for greeting_type, keywords in GREETING_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundary regex to avoid false positives
            # e.g., "good" shouldn't match "goodbye" or "goodness"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                print(f"[GREETING] Regex match: '{keyword}' matched in '{text_lower}' (type: {greeting_type})")
                return greeting_type
    
    # STEP 2: Try fuzzy matching for typos and variations (medium-high confidence)
    # Only use fuzzy matching if message is short (likely to be a greeting)
    if len(text_lower.split()) <= 5:  # Max 5 words for greeting
        best_match = None
        best_score = 0
        best_type = None
        
        for greeting_type, keywords in GREETING_KEYWORDS.items():
            for keyword in keywords:
                # Use token_set_ratio for better matching with word order variations
                score = fuzz.token_set_ratio(text_lower, keyword)
                
                # Require 75% confidence for fuzzy match (helps avoid false positives)
                if score >= 75 and score > best_score:
                    best_score = score
                    best_match = keyword
                    best_type = greeting_type
        
        if best_type:
            print(f"[GREETING] Fuzzy match: '{best_match}' matched in '{text_lower}' with {best_score}% confidence (type: {best_type})")
            return best_type
    
    return None

def get_response_for_greeting(greeting_type: str, name: str) -> str:
    response_map = {
        'hello': get_random_greeting_response,
        'hi': get_random_greeting_response,
        'hey': get_random_greeting_response,
        'good_morning': get_random_good_morning_message,
        'good_night': get_random_good_night_message,
        'good_afternoon': get_random_good_afternoon_message,
        'good_evening': get_random_good_evening_message,
        'how_are_you': get_random_how_are_you_response,
        'thank_you': get_random_thank_you_response,
        'bye': get_random_bye_response,
        'laugh': get_random_laugh_response,
        'sad': get_random_sad_response,
    }
    
    if greeting_type in response_map:
        return response_map[greeting_type](name)
    return None
