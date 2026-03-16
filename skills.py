import subprocess
import os
import datetime
import threading
import math
import re
import webbrowser
import urllib.parse
import pyjokes

try:
    import wikipedia
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False

# ── App name → macOS bundle map ───────────────────────────────────────────────
APP_MAP = {
    "safari":       "Safari",
    "chrome":       "Google Chrome",
    "firefox":      "Firefox",
    "mail":         "Mail",
    "calendar":     "Calendar",
    "notes":        "Notes",
    "maps":         "Maps",
    "messages":     "Messages",
    "facetime":     "FaceTime",
    "spotify":      "Spotify",
    "music":        "Music",
    "finder":       "Finder",
    "terminal":     "Terminal",
    "vs code":      "Visual Studio Code",
    "vscode":       "Visual Studio Code",
    "word":         "Microsoft Word",
    "excel":        "Microsoft Excel",
    "powerpoint":   "Microsoft PowerPoint",
    "slack":        "Slack",
    "zoom":         "zoom.us",
    "discord":      "Discord",
    "whatsapp":     "WhatsApp",
    "photos":       "Photos",
    "preview":      "Preview",
    "calculator":   "Calculator",
    "contacts":     "Contacts",
    "settings":     "System Preferences",
}

def _run(cmd: str) -> str:
    """Run a shell command, return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    return result.stdout.strip()

def _osascript(script: str):
    subprocess.run(["osascript", "-e", script])

# ── Individual skill functions ────────────────────────────────────────────────

def skill_greeting(*_) -> str:
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning! How can I assist you today?"
    elif hour < 17:
        return "Good afternoon! What can I do for you?"
    else:
        return "Good evening! What do you need?"

def skill_get_time(*_) -> str:
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p')}."

def skill_get_date(*_) -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."

def skill_get_day(*_) -> str:
    return f"Today is {datetime.datetime.now().strftime('%A')}."

def skill_tell_joke(*_) -> str:
    return pyjokes.get_joke()

def skill_web_search(data: dict, raw: str) -> str:
    query = data.get("query", raw).strip()
    if not query:
        return "What would you like me to search for?"

    if WIKI_AVAILABLE:
        try:
            wikipedia.set_lang("en")
            # Get a short 1-sentence summary for speaking
            summary = wikipedia.summary(query, sentences=1, auto_suggest=True)
            # Clean up brackets like [1], [citation needed] etc.
            import re
            summary = re.sub(r'\[.*?\]', '', summary).strip()
            # Limit length so TTS doesn't take forever
            if len(summary) > 300:
                summary = summary[:300].rsplit(' ', 1)[0] + "."
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            try:
                summary = wikipedia.summary(e.options[0], sentences=1)
                import re
                summary = re.sub(r'\[.*?\]', '', summary).strip()
                return summary
            except Exception:
                pass
        except wikipedia.exceptions.PageError:
            pass
        except Exception:
            pass

    # Fallback: open browser
    encoded = urllib.parse.quote(query)
    webbrowser.open(f"https://duckduckgo.com/?q={encoded}")
    return f"I couldn't find a direct answer, so I've opened a search for {query} in your browser."

def skill_open_app(data: dict, raw: str) -> str:
    app_key = data.get("app", "").lower()
    app_name = APP_MAP.get(app_key)

    if app_name:
        _run(f"open -a '{app_name}'")
        return f"Opening {app_name}."
    elif app_key:
        # Try anyway with the raw name
        result = subprocess.run(
            ["open", "-a", app_key],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Opening {app_key}."
        else:
            return f"I couldn't find an app named {app_key}. Please check the name."
    else:
        return "Which app would you like me to open?"

def skill_close_app(data: dict, raw: str) -> str:
    app_key = data.get("app", "").lower()
    app_name = APP_MAP.get(app_key, app_key)
    if app_name:
        _osascript(f'quit app "{app_name}"')
        return f"Closing {app_name}."
    return "Which app should I close?"

def skill_volume_up(*_) -> str:
    _osascript("set volume output volume (output volume of (get volume settings) + 10)")
    return "Volume increased."

def skill_volume_down(*_) -> str:
    _osascript("set volume output volume (output volume of (get volume settings) - 10)")
    return "Volume decreased."

def skill_volume_mute(*_) -> str:
    _osascript("set volume with output muted")
    return "Muted."

def skill_screenshot(*_) -> str:
    path = os.path.expanduser(f"~/Desktop/jarvis_screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    _run(f"screencapture '{path}'")
    return f"Screenshot saved to your Desktop."

def skill_system_shutdown(*_) -> str:
    _osascript('tell app "System Events" to shut down')
    return "Shutting down your Mac."

def skill_system_restart(*_) -> str:
    _osascript('tell app "System Events" to restart')
    return "Restarting your Mac."

def skill_system_lock(*_) -> str:
    _run("pmset displaysleepnow")
    return "Screen locked."

def skill_calculate(data: dict, raw: str) -> str:
    expr = data.get("expression", "")
    # Also try extracting directly from raw
    if not expr:
        expr = re.sub(r"[a-zA-Z\s]", "", raw)
    try:
        # Safe eval with math only
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        result = eval(expr, {"__builtins__": {}}, allowed)
        return f"The answer is {result}."
    except Exception:
        return "I couldn't calculate that. Please phrase it like 'calculate 25 times 4'."

def skill_set_timer(data: dict, raw: str) -> str:
    seconds = data.get("seconds", 60)

    def timer_done():
        import pyttsx3
        e = pyttsx3.init()
        e.say("Time is up!")
        e.runAndWait()

    threading.Timer(float(seconds), timer_done).start()
    mins = seconds // 60
    secs = seconds % 60
    label = f"{mins} minute{'s' if mins != 1 else ''}" if mins else f"{secs} second{'s' if secs != 1 else ''}"
    return f"Timer set for {label}."

def skill_set_reminder(data: dict, raw: str) -> str:
    # Simple: open Reminders app with the command as context
    _run("open -a Reminders")
    return "Opening Reminders app for you."

def skill_get_weather(*_) -> str:
    # Open weather in browser (requires no API key)
    webbrowser.open("https://wttr.in")
    return "Opening weather forecast in your browser."

def skill_get_news(*_) -> str:
    webbrowser.open("https://news.google.com")
    return "Opening Google News in your browser."

def skill_play_music(*_) -> str:
    _run("open -a Music")
    return "Opening Music app."

def skill_unknown(*_) -> str:
    return "I'm not sure how to help with that yet. Try rephrasing or ask me to search the web."

# ── Skill router ──────────────────────────────────────────────────────────────
SKILLS = {
    "greeting":         skill_greeting,
    "get_time":         skill_get_time,
    "get_date":         skill_get_date,
    "get_day":          skill_get_day,
    "tell_joke":        skill_tell_joke,
    "web_search":       skill_web_search,
    "open_app":         skill_open_app,
    "close_app":        skill_close_app,
    "volume_up":        skill_volume_up,
    "volume_down":      skill_volume_down,
    "volume_mute":      skill_volume_mute,
    "screenshot":       skill_screenshot,
    "system_shutdown":  skill_system_shutdown,
    "system_restart":   skill_system_restart,
    "system_lock":      skill_system_lock,
    "calculate":        skill_calculate,
    "set_timer":        skill_set_timer,
    "set_reminder":     skill_set_reminder,
    "get_weather":      skill_get_weather,
    "get_news":         skill_get_news,
    "play_music":       skill_play_music,
}

def execute(intent: str, data: dict, raw: str) -> str:
    skill_fn = SKILLS.get(intent, skill_unknown)
    try:
        return skill_fn(data, raw)
    except Exception as e:
        print(f"[Skill error: {e}]")
        return "Something went wrong while handling that request."