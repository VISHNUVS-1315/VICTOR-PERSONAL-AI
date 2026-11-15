"""
VICTOR Cognitive Intelligence Engine
Powered by local Ollama (Qwen 3.5 9B).
Handles natural conversational dialog in English and Tamil/Tanglish,
context management, intent parsing for secure computer automation,
and automatic personal fact extraction.
"""

import json
import re
import threading
import uuid
from typing import Dict, Any, List, Optional, Tuple

import requests

from src.actions.computer_control import computer
from src.config.settings import settings
from src.memory.store import (
    save_memory,
    get_memories,
    delete_memory,
    format_memories_for_prompt,
    save_conversation_turn,
    get_recent_conversation
)

OLLAMA_HOST = settings.get("ollama.host", "http://localhost:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}{settings.get('ollama.chat_endpoint', '/api/chat')}"
MODEL = settings.get("ollama.model", "qwen3.5:9b")

SYSTEM_PROMPT_TEMPLATE = """You are VICTOR, a professional personal AI assistant running locally on Windows 11 for Operator Vishnu. You speak through a text-to-speech voice, so everything you write is read aloud.

Voice and style:
1. Speak in plain, natural sentences. Never use emoji, emoticons, decorative symbols, or markdown formatting (no asterisks, hashes, bullets, or backticks).
2. Be concise. Answer simple questions in one or two sentences. Only give a longer explanation when the topic genuinely needs it.
3. Sound like a capable human assistant: calm, direct, no filler, no introductions like "Certainly" or "As an AI".
4. Do not repeat information you already gave earlier in this conversation.

Accuracy:
5. Never invent facts, figures, APIs, or file names. If you do not know, say plainly what you do not know and what you would need to check.
6. If a request is ambiguous or missing a key detail, ask one short clarifying question instead of guessing.
7. When you give numbers or steps, keep them realistic and check they are internally consistent.

Capabilities:
8. You can control the computer when explicitly asked, by emitting an action tag:
   - Open App: [ACTION: {{"action": "open_app", "target": "<app_name>"}}]
     (Allowed: code, cursor, chrome, brave, msedge, notepad, calc, wt/terminal, cmd, powershell, taskmgr, explorer, spotify, discord)
   - Launch Website: [ACTION: {{"action": "launch_website", "query": "<url_or_site>"}}]
   - Open Folder: [ACTION: {{"action": "open_folder", "folder": "<downloads|documents|desktop|projects>"}}]
   - Take Screenshot: [ACTION: {{"action": "screenshot"}}]
   - Volume Control: [ACTION: {{"action": "volume_set", "level": <0-100>}}], [ACTION: {{"action": "volume_change", "delta": <+/-10>}}], [ACTION: {{"action": "volume_mute", "mute": <true|false>}}]
   - Media Control: [ACTION: {{"action": "media_control", "command": "<play_pause|next|prev|stop>"}}]
   - System Diagnostics: [ACTION: {{"action": "system_report"}}]
   - Date and Time: [ACTION: {{"action": "query_time"}}]
9. Never claim an action succeeded. The system executes the tag and reports the real result.
10. You understand English and Tamil/Tanglish and reply in the language the user used.

Permanent memory context:
{saved_memories}
"""


class VictorBrain:
    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.history: List[Dict[str, str]] = []
        self.max_history_turns = int(settings.get("ollama.max_context_turns", 12))
        # One inference at a time: never run parallel requests against the same model.
        self._infer_lock = threading.Lock()

    @staticmethod
    def clean_reply(text: str) -> str:
        """Remove emoji and decorative symbols so the voice never reads them aloud."""
        if not text:
            return ""
        # Emoji / pictograph ranges
        text = re.sub(
            "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
            "\U0001F1E6-\U0001F1FF\uFE0F\u200D]",
            "",
            text,
        )
        # Markdown emphasis / bullet noise that sounds wrong when spoken
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"[*_`#>]+", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def reset_conversation(self):
        """Clear active in-memory conversation context."""
        self.history.clear()
        self.session_id = str(uuid.uuid4())[:8]
        return "Conversation context reset. Victor is standing by."

    def check_connection(self) -> Tuple[bool, str]:
        """Check if Ollama service is reachable and model is available."""
        try:
            resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2.5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                if any(MODEL in m for m in models):
                    return True, f"Ollama online with model {MODEL}."
                return True, f"Ollama online, but active model '{MODEL}' not found. Available: {', '.join(models)}"
            return False, f"Ollama returned HTTP status {resp.status_code}."
        except Exception as e:
            return False, f"Could not connect to Ollama at {OLLAMA_HOST}: {e}"

    def _execute_embedded_actions(self, text: str) -> Tuple[str, List[str]]:
        """Parse [ACTION: {...}] tags in LLM output, execute them safely, and return modified response."""
        action_pattern = r"\[ACTION:\s*(\{.*?\})\s*\]"
        matches = re.findall(action_pattern, text)
        executed_notes = []

        clean_text = re.sub(action_pattern, "", text).strip()

        for raw_json in matches:
            try:
                data = json.loads(raw_json)
                act_type = data.get("action")

                if act_type == "open_app":
                    ok, msg = computer.open_application(data.get("target", ""))
                    executed_notes.append(msg)

                elif act_type == "launch_website":
                    ok, msg = computer.launch_website(data.get("query", ""))
                    executed_notes.append(msg)

                elif act_type == "open_folder":
                    ok, msg = computer.open_folder(data.get("folder", ""))
                    executed_notes.append(msg)

                elif act_type == "screenshot":
                    ok, msg = computer.take_screenshot()
                    executed_notes.append(msg)

                elif act_type == "volume_set":
                    ok, msg = computer.set_volume(data.get("level", 50))
                    executed_notes.append(msg)

                elif act_type == "volume_change":
                    ok, msg = computer.change_volume(data.get("delta", 10))
                    executed_notes.append(msg)

                elif act_type == "volume_mute":
                    ok, msg = computer.set_mute(data.get("mute", True))
                    executed_notes.append(msg)

                elif act_type == "media_control":
                    ok, msg = computer.media_control(data.get("command", "play_pause"))
                    executed_notes.append(msg)

                elif act_type == "system_report":
                    rep = computer.get_system_report()
                    executed_notes.append(rep)

                elif act_type == "query_time":
                    time_str = computer.get_time_and_date()
                    executed_notes.append(time_str)

            except Exception as e:
                executed_notes.append(f"Action execution error: {e}")

        final_reply = clean_text
        if executed_notes:
            # If model produced no text or minimal text, use action result directly
            if not final_reply or len(final_reply) < 5:
                final_reply = " ".join(executed_notes)
            else:
                # Add confirmed action notes if not already reflected
                final_reply = f"{final_reply}\n\n[Action Completed: {', '.join(executed_notes)}]"

        return final_reply, executed_notes

    def detect_and_save_fact(self, user_message: str) -> Optional[str]:
        """Extract personal facts using fast local heuristics without duplicate LLM queries."""
        text = user_message.strip()
        lower = text.lower()

        patterns = [
            (r"(?i)\bi am working on ([\w\s\-\.]{4,60})\b", "Operator is working on {0}."),
            (r"(?i)\bi am building ([\w\s\-\.]{4,60})\b", "Operator is building {0}."),
            (r"(?i)\bmy project is ([\w\s\-\.]{4,60})\b", "Operator project: {0}."),
            (r"(?i)\bi want to become an? ([\w\s\-\.]{4,60})\b", "Operator career goal: become an {0}."),
            (r"(?i)\bi am studying ([\w\s\-\.]{4,60})\b", "Operator is studying {0}."),
            (r"(?i)\bmy name is ([\w\s]{2,30})\b", "Operator name is {0}."),
            (r"(?i)\bi prefer ([\w\s\-\.]{4,60})\b", "Operator preference: prefers {0}.")
        ]

        for pat, template in patterns:
            m = re.search(pat, text)
            if m:
                extracted = m.group(1).strip(" .!?,")
                fact = template.format(extracted)
                save_memory(fact, category="preference")
                return fact
        return None

    def query(self, user_message: str) -> str:
        """Process user message, maintain context, handle computer actions, and return response."""
        clean_user = user_message.strip()
        if not clean_user:
            return "How may I assist you?"

        lower_msg = clean_user.lower()

        # Direct Fast-Track Commands
        if lower_msg in ("what time is it", "what's the time", "tell me the time", "current time", "what is the date"):
            return computer.get_time_and_date()

        if lower_msg in ("system status", "system diagnostics", "system report", "hardware status", "check cpu"):
            return computer.get_system_report()

        if lower_msg in ("take a screenshot", "capture screen", "screenshot"):
            ok, msg = computer.take_screenshot()
            return msg

        if lower_msg in ("mute", "mute volume", "mute audio"):
            ok, msg = computer.set_mute(True)
            return msg

        if lower_msg in ("unmute", "unmute volume", "unmute audio"):
            ok, msg = computer.set_mute(False)
            return msg

        if lower_msg.startswith("volume to ") or lower_msg.startswith("set volume to "):
            nums = re.findall(r"\d+", lower_msg)
            if nums:
                ok, msg = computer.set_volume(int(nums[0]))
                return msg

        if lower_msg in ("stop talking", "stop speaking", "be quiet", "stop voice"):
            from src.voice.tts import tts_engine
            tts_engine.stop()
            return "Speech output stopped."

        # Power mode fast-track commands
        if lower_msg in ("low power mode", "set mode to low power", "enable low power mode", "low power"):
            settings.set_power_mode("low_power")
            return "Power mode switched to Low Power. UI rendering and background telemetry throttled for minimum CPU and GPU load."

        if lower_msg in ("balanced mode", "set mode to balanced", "enable balanced mode", "balanced"):
            settings.set_power_mode("balanced")
            return "Power mode switched to Balanced. Moderate animations and telemetry enabled."

        if lower_msg in ("performance mode", "set mode to performance", "enable performance mode", "performance"):
            settings.set_power_mode("performance")
            return "Power mode switched to Performance. Full visual HUD effects and high-frequency telemetry enabled."

        # Log user query to persistent memory
        save_conversation_turn(self.session_id, "user", clean_user)

        # Check for explicit memory commands
        if lower_msg == "memories" or lower_msg == "show memories":
            memories = get_memories()
            if not memories:
                return "You have no saved memories in my database."
            return "Here are your saved memories:\n" + "\n".join(
                f"{m['id']}. [{m['category'].upper()}] {m['content']}" for m in memories
            )

        if lower_msg.startswith("remember that ") or lower_msg.startswith("remember "):
            fact = clean_user[13:] if lower_msg.startswith("remember that ") else clean_user[9:]
            res = save_memory(fact, category="user_note")
            return f"Understood. {res}"

        if lower_msg.startswith("forget memory ") or lower_msg.startswith("forget "):
            nums = re.findall(r"\d+", lower_msg)
            if nums:
                mem_id = int(nums[0])
                if delete_memory(mem_id):
                    return f"Memory #{mem_id} has been erased from my database."
                return f"Memory #{mem_id} could not be found."

        # Format system prompt with latest stored memories
        saved_memories_str = format_memories_for_prompt(limit=15)
        system_content = SYSTEM_PROMPT_TEMPLATE.format(saved_memories=saved_memories_str)

        # Build message history for Ollama
        messages = [{"role": "system", "content": system_content}]

        # Add recent conversation turns
        for turn in self.history[-self.max_history_turns:]:
            messages.append(turn)

        messages.append({"role": "user", "content": clean_user})

        # Query local Ollama (serialised, model kept warm to avoid reload costs)
        try:
            with self._infer_lock:
                response = requests.post(
                    OLLAMA_CHAT_URL,
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "stream": False,
                        "keep_alive": "30m",
                        "options": {
                            "temperature": 0.7,
                            "num_ctx": 4096,
                        }
                    },
                    timeout=120
                )
            response.raise_for_status()

            raw_reply = self.clean_reply(response.json()["message"]["content"])

            # Parse and execute embedded actions if present
            final_reply, executed_actions = self._execute_embedded_actions(raw_reply)

            # Update in-memory context history
            self.history.append({"role": "user", "content": clean_user})
            self.history.append({"role": "assistant", "content": final_reply})
            if len(self.history) > self.max_history_turns * 2:
                self.history = self.history[-self.max_history_turns * 2:]

            # Log assistant reply to persistent store
            save_conversation_turn(self.session_id, "assistant", final_reply)

            # Instant local fact extraction (zero LLM overhead)
            self.detect_and_save_fact(clean_user)

            return final_reply

        except requests.exceptions.ConnectionError:
            err_msg = (
                f"Connection to Ollama failed. Please ensure the Ollama service is active. "
                f"You can start it by opening terminal and typing: 'ollama serve'."
            )
            return err_msg
        except Exception as e:
            return f"Victor inference error: {e}"


# Global instance
victor_brain = VictorBrain()


def ask_victor(message: str) -> str:
    """Convenience functional bridge for backward compatibility."""
    return victor_brain.query(message)


def detect_memory(message: str) -> Optional[str]:
    return victor_brain.detect_and_save_fact(message)


def show_memories() -> str:
    mems = get_memories()
    if not mems:
        return "No saved memories."
    return "\n".join(f"{m['id']}. {m['content']}" for m in mems)
