import speech_recognition as sr
import pyttsx3
import time
import threading
from brain import understand
from skills import execute

# ── TTS setup 
try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    engine.setProperty("voice", voices[0].id)
    TTS_OK = True
    print("[OK] Text-to-speech ready.")
except Exception as e:
    TTS_OK = False
    print(f"[WARN] TTS failed: {e}")

def speak(text: str):
    print(f"\nJarvis: {text}\n")
    if not TTS_OK:
        return
    try:
        # Break long text into sentences so pyttsx3 doesn't choke
        sentences = text.replace("! ", ". ").replace("? ", ". ").split(". ")
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                engine.say(sentence)
                engine.runAndWait()
    except Exception as e:
        print(f"[TTS error: {e}]")

# ── Microphone 
recognizer = sr.Recognizer()
recognizer.pause_threshold = 0.6
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 250

print("Calibrating microphone once...")
try:
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print(f"[OK] Mic calibrated. Energy threshold: {recognizer.energy_threshold:.0f}")
except Exception as e:
    print(f"[WARN] Mic calibration failed: {e}")

WAKE_WORD = "jarvis"
MIC_FAIL_COUNT = 0
MAX_MIC_FAILS = 3

# ── Listen function ─────────
def listen_with_timeout(prompt="Listening...", timeout_seconds=8):
    result = {"text": None, "error": None}

    def _listen():
        try:
            with sr.Microphone() as source:
                print(prompt)
                # Only do a tiny re-adjust (0.1s) on each listen, not 0.5s
                recognizer.adjust_for_ambient_noise(source, duration=0.1)
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
                text = recognizer.recognize_google(
                    audio,
                    language="en-US",
                    show_all=False
                ).lower()
                result["text"] = text
        except sr.WaitTimeoutError:
            result["error"] = "timeout"
        except sr.UnknownValueError:
            result["error"] = "unclear"
        except sr.RequestError as e:
            result["error"] = f"request_error:{e}"
        except Exception as e:
            result["error"] = f"unknown:{e}"

    t = threading.Thread(target=_listen, daemon=True)
    t.start()
    t.join(timeout=timeout_seconds)

    if t.is_alive():
        return None, "hard_timeout"

    return result["text"], result["error"]

def listen_once(prompt="Listening..."):
    global MIC_FAIL_COUNT
    text, error = listen_with_timeout(prompt)

    if text:
        MIC_FAIL_COUNT = 0
        print(f"You said: {text}")
        return text

    if error == "timeout":
        return None
    elif error == "unclear":
        return None
    elif error and "request_error" in error:
        speak("My speech service seems offline. Check your internet.")
        return None
    elif error == "hard_timeout":
        MIC_FAIL_COUNT += 1
        speak("Microphone isn't responding. Check mic permissions in System Settings.")
        return None
    else:
        print(f"[Listen error: {error}]")
        return None

def text_fallback():
    try:
        typed = input("(Mic unavailable — type your command): ").strip().lower()
        return typed if typed else None
    except (EOFError, KeyboardInterrupt):
        return None

# ── Main loop ─────────────────────────────────────────────────────────────────
def run():
    print("\n" + "="*50)
    print("       JARVIS — Voice Assistant")
    print("="*50 + "\n")
    speak("Jarvis online. Say Jarvis to wake me up.")
    print(f"[Standby — say '{WAKE_WORD}' to activate]\n")

    while True:
        try:
            if MIC_FAIL_COUNT >= MAX_MIC_FAILS:
                print("[Text mode active]")
                phrase = text_fallback()
            else:
                phrase = listen_once("Standby — listening for wake word...")

            if not phrase:
                continue

            if WAKE_WORD in phrase:
                speak("Yes?")

                command = listen_once("Listening for your command...")
                if not command:
                    speak("I didn't catch that. Try again.")
                    continue

                if any(w in command for w in [
                    "goodbye", "bye", "shut down jarvis",
                    "exit jarvis", "quit jarvis", "stop"
                ]):
                    speak("Goodbye!")
                    break

                intent, data = understand(command)
                print(f"[Intent: {intent}] [Data: {data}]")
                response = execute(intent, data, command)
                speak(response)

            time.sleep(0.05)

        except KeyboardInterrupt:
            speak("Goodbye!")
            break
        except Exception as e:
            print(f"[Error: {e}]")
            time.sleep(1)

if __name__ == "__main__":
    run()