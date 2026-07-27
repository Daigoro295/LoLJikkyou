import json
import urllib.parse
import urllib.request
import winsound

from config import CONNECTION_ERRORS, VOICEVOX_BASE_URL, VOICEVOX_SPEAKER_ID, VOICEVOX_TIMEOUT_SECONDS


def speak(text: str, speaker: int = VOICEVOX_SPEAKER_ID) -> None:
    """VOICEVOX APIでテキストを音声合成し再生する"""
    query = urllib.parse.urlencode({"text": text, "speaker": speaker})

    try:
        audio_query_request = urllib.request.Request(
            f"{VOICEVOX_BASE_URL}/audio_query?{query}", method="POST"
        )
        with urllib.request.urlopen(audio_query_request, timeout=VOICEVOX_TIMEOUT_SECONDS) as response:
            audio_query = json.load(response)

        synthesis_request = urllib.request.Request(
            f"{VOICEVOX_BASE_URL}/synthesis?speaker={speaker}",
            data=json.dumps(audio_query).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(synthesis_request, timeout=VOICEVOX_TIMEOUT_SECONDS) as response:
            wav_data = response.read()
    except CONNECTION_ERRORS as e:
        print(f"VOICEVOX APIへの接続に失敗しました(エンジンが起動していない可能性があります): {e}")
        return

    winsound.PlaySound(wav_data, winsound.SND_MEMORY)


def play_test_voice() -> None:
    """LoLクライアント不要でVOICEVOXの動作(接続先・話者ID)を確認するためのテスト音声を再生する"""
    speak(f"こんにちは、音声テストです。話者IDは{VOICEVOX_SPEAKER_ID}番です。")
