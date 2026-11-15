
from src.io.stt import listen
from src.io.tts import speak
from src.brain.llm import ask_victor
import re


def main():
    print("\n===== VICTOR AI ASSISTANT =====")

    speak("Hello. I am Victor. I am ready to assist you.")

    while True:
        user_text = listen()

        if not user_text:
            continue

        command = re.sub(
            r"[^a-z ]", "", user_text.lower()
        ).strip()

        if command in (
            "exit",
            "stop",
            "stop victor",
            "goodbye"
        ):
            speak("Goodbye. See you again.")
            break

        print("\nYou:", user_text)

        response = ask_victor(user_text)

        speak(response)


if __name__ == "__main__":
    main()
