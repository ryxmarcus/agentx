#!/usr/bin/env python3
"""ElevenLabs Voice Service for iTOPAZ Agent Ecosystem.

Provides text-to-speech audio synthesis, caching, status alerts,
job application voice notifications, and mock interview practice audio.
"""

import os
import sys
import hashlib
import requests
import urllib3
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

urllib3.disable_warnings()

BASE_DIR = Path(os.environ.get("ITOPAZ_WORKSPACE_ROOT", Path(__file__).resolve().parent.parent)).resolve()
SECRETS_DIR = BASE_DIR / "secrets"
AUDIO_CACHE_DIR = BASE_DIR / "artifacts" / "audio"
PLAY_SCRIPT = BASE_DIR / "scripts" / "play_audio.ps1"

# Voice Roster
VOICES = {
    "sarah": "EXAVITQu4vr4xnSDxMaL",    # Default: Mature, Reassuring, Confident
    "george": "JBFqnCBsd6RMkjVDRZzb",   # Professional Technical Interviewer (British)
    "alice": "Xb7hH8MSUJpSbSDYk0k2",    # Clear Educator (British)
    "charlie": "IKne3meq5aSn9XLyUdCD",  # Deep, Energetic (Australian)
    "roger": "CwhRBWXzGAHq8TQ4Fs17",    # Laid-Back, Resonant (American)
}

DEFAULT_MODEL = "eleven_turbo_v2_5"


class VoiceService:
    """Manages ElevenLabs TTS synthesis, caching, and playback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_api_key(self) -> Optional[str]:
        # 1. Environment variable
        if os.environ.get("ELEVENLABS_API_KEY"):
            return os.environ["ELEVENLABS_API_KEY"].strip()

        # 2. secrets/elevenlabs_key.txt
        p = SECRETS_DIR / "elevenlabs_key.txt"
        if p.is_file():
            content = p.read_text(encoding="utf-8").strip()
            if content:
                return content.splitlines()[0].strip()

        # 3. .env file
        env_file = BASE_DIR / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    return line.split("=", 1)[1].strip()

        return None

    def check_quota(self) -> Dict[str, Any]:
        """Check ElevenLabs account subscription and remaining quota."""
        if not self.api_key:
            return {"error": "No ElevenLabs API key found"}
        headers = {"xi-api-key": self.api_key}
        res = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            data = res.json().get("subscription", {})
            return {
                "tier": data.get("tier"),
                "used_chars": data.get("character_count"),
                "limit_chars": data.get("character_limit"),
                "remaining_chars": data.get("character_limit", 0) - data.get("character_count", 0),
            }
        return {"error": f"API error HTTP {res.status_code}: {res.text[:150]}"}

    def synthesize(
        self,
        text: str,
        voice_name: str = "sarah",
        model_id: str = DEFAULT_MODEL,
        output_file: Optional[Path] = None,
        use_cache: bool = True
    ) -> Optional[Path]:
        """Synthesize speech audio from text using ElevenLabs."""
        if not self.api_key:
            print("[VoiceService] Error: No API key available.")
            return None

        voice_id = VOICES.get(voice_name.lower(), VOICES["sarah"])

        # Determine target file
        if not output_file:
            # Hash text + voice to avoid redundant API calls
            text_hash = hashlib.md5(f"{voice_id}_{text}".encode('utf-8')).hexdigest()[:12]
            output_file = AUDIO_CACHE_DIR / f"tts_{text_hash}.mp3"

        if use_cache and output_file.exists() and output_file.stat().st_size > 0:
            return output_file

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8
            }
        }

        try:
            res = requests.post(url, json=payload, headers=headers, verify=False, timeout=20)
            if res.status_code == 200:
                with open(output_file, 'wb') as f:
                    f.write(res.content)
                return output_file
            else:
                print(f"[VoiceService] Synthesis failed (HTTP {res.status_code}): {res.text[:120]}")
                return None
        except Exception as e:
            print(f"[VoiceService] Network exception: {e}")
            return None

    def play(self, audio_path: Path, async_play: bool = True) -> bool:
        """Play audio file on Windows host using play_audio.ps1."""
        if not audio_path or not audio_path.exists():
            return False

        if not PLAY_SCRIPT.exists():
            # Create helper script if missing
            PLAY_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
            PLAY_SCRIPT.write_text(
                "param([string]$AudioPath)\n"
                "Add-Type -AssemblyName presentationCore\n"
                "$m = New-Object System.Windows.Media.MediaPlayer\n"
                "$m.Open([System.Uri]$AudioPath)\n"
                "$m.Play()\n"
                "Start-Sleep -Seconds 4\n"
                "$m.Close()\n",
                encoding="utf-8"
            )

        cmd = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", str(PLAY_SCRIPT),
            "-AudioPath", str(audio_path)
        ]

        try:
            if async_play:
                subprocess.Popen(cmd)
            else:
                subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            print(f"[VoiceService] Playback error: {e}")
            return False

    def speak(self, text: str, voice_name: str = "sarah", play_now: bool = True) -> Optional[Path]:
        """One-step helper to synthesize and play spoken audio."""
        audio_file = self.synthesize(text, voice_name=voice_name)
        if audio_file and play_now:
            self.play(audio_file)
        return audio_file

    def notify_application_event(self, company: str, role: str, status: str = "submitted", play: bool = True):
        """Voice notification for job application dispatch."""
        if status == "submitted":
            msg = f"Job application to {company} for {role} has been submitted successfully."
        elif status == "staged":
            msg = f"Application for {company} is staged. Captcha resolution required in browser."
        else:
            msg = f"Status update for {company}: {status}."
        return self.speak(msg, voice_name="sarah", play_now=play)

    def speak_interview_question(self, question: str, voice_name: str = "george", play: bool = True):
        """Play technical mock interview prompt."""
        return self.speak(question, voice_name=voice_name, play_now=play)


if __name__ == "__main__":
    service = VoiceService()
    print("Quota status:", service.check_quota())
    print("Testing VoiceService notification...")
    f = service.speak("iTopaz Agent Voice Service is fully operational.", voice_name="sarah", play_now=False)
    print("Generated:", f)
