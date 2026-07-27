import http.client
import os
import ssl

# ゲーム終了時の切断など、urlopen中に発生しうる通信エラー全般
CONNECTION_ERRORS = (OSError, http.client.HTTPException)


def _load_env_file(path: str = ".env") -> None:
    """.envファイルを読み込みos.environに反映する(python-dotenv不使用、標準ライブラリのみ)"""
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

LIVE_CLIENT_BASE_URL = os.environ.get("LIVE_CLIENT_BASE_URL", "https://127.0.0.1:2999")
LIVE_CLIENT_DATA_URL = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/activeplayer"
GAME_EVENTS_URL = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/eventdata"
ALL_PLAYERS_URL = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/playerlist"

# LoLのLive Client Data APIは自己署名証明書を使用するため検証をスキップする
UNVERIFIED_SSL_CONTEXT = ssl._create_unverified_context()

VOICEVOX_BASE_URL = os.environ.get("VOICEVOX_BASE_URL", "http://127.0.0.1:50021")
VOICEVOX_SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "1"))  # ずんだもん(ノーマル)

POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "1.0"))

# 空文字の場合はLLMによる実況生成を行わずテンプレートの実況文をそのまま使用する
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
