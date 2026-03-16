import spacy
import re

nlp = spacy.load("en_core_web_sm")

# Stop words to strip before matching intent
STOP_WORDS = {
    "please", "can", "you", "could", "would", "jarvis",
    "hey", "hi", "hello", "tell", "me", "about", "the",
    "a", "an", "i", "my", "what", "is", "are", "do",
    "did", "does", "how", "who", "where", "when", "why",
    "give", "show", "find", "get", "make"
}

# Intent keyword map — order matters (more specific first)
INTENT_PATTERNS = [
    # System control
    (["shutdown", "shut down", "turn off"],             "system_shutdown"),
    (["restart", "reboot"],                             "system_restart"),
    (["lock screen", "lock"],                           "system_lock"),
    (["volume up", "increase volume", "louder"],        "volume_up"),
    (["volume down", "decrease volume", "quieter"],     "volume_down"),
    (["mute", "silence"],                               "volume_mute"),
    (["screenshot", "screen shot"],                     "screenshot"),

    # App/file control
    (["open", "launch", "start"],                       "open_app"),
    (["close", "quit", "exit"],                         "close_app"),

    # Web search
    (["search for", "look up", "google", "find"],       "web_search"),
    (["who is", "who are", "who was", "who were"],      "web_search"),
    (["what is", "what are", "what was"],               "web_search"),
    (["tell me about", "explain"],                      "web_search"),

    # Predefined commands
    (["time", "what time"],                             "get_time"),
    (["date", "what date", "today"],                    "get_date"),
    (["day", "what day"],                               "get_day"),
    (["joke", "funny", "make me laugh"],                "tell_joke"),
    (["weather", "temperature", "forecast"],            "get_weather"),
    (["news"],                                          "get_news"),
    (["play music", "play song", "music"],              "play_music"),
    (["timer", "set timer"],                            "set_timer"),
    (["reminder", "remind me"],                         "set_reminder"),
    (["calculate", "what is", "compute", "math"],       "calculate"),

    # Greeting
    (["hello", "hi", "hey", "good morning",
      "good afternoon", "good evening"],                "greeting"),
]

def clean_query(text: str) -> str:
    """Remove stop words and return the core query."""
    doc = nlp(text.lower())
    tokens = [
        token.text for token in doc
        if not token.is_punct
        and not token.is_space
        and token.text not in STOP_WORDS
    ]
    return " ".join(tokens).strip()

def extract_app_name(text: str) -> str:
    """Pull the app name from commands like 'open safari'."""
    for trigger in ["open", "launch", "start", "close", "quit"]:
        if trigger in text:
            after = text.split(trigger, 1)[-1].strip()
            return after.split()[0] if after else ""
    return ""

def extract_search_query(text: str) -> str:
    """Strip preamble from search/question commands."""
    prefixes = [
        "search for", "look up", "google", "find",
        "who is", "who are", "who was", "what is",
        "what are", "what was", "tell me about",
        "explain", "who", "what"
    ]
    t = text.lower()
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].strip()
            break
    return t

def understand(text: str) -> tuple[str, dict]:
    """Return (intent, data_dict) from raw user speech."""
    text = text.lower().strip()

    # Match intents
    for keywords, intent in INTENT_PATTERNS:
        if any(kw in text for kw in keywords):
            data = {}

            if intent in ("web_search",):
                data["query"] = extract_search_query(text)
                # NLP: extract named entities as hint
                doc = nlp(text)
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                if entities:
                    data["entities"] = entities

            elif intent in ("open_app", "close_app"):
                data["app"] = extract_app_name(text)

            elif intent == "calculate":
                # Extract the math expression
                expr = re.sub(r"[^0-9+\-*/().\s]", "", text)
                data["expression"] = expr.strip()

            elif intent == "set_timer":
                nums = re.findall(r"\d+", text)
                data["seconds"] = int(nums[0]) * 60 if nums else 60
                data["unit"] = "minutes" if "minute" in text else "seconds"

            return intent, data

    # Fallback: treat entire utterance as search
    return "web_search", {"query": clean_query(text)}