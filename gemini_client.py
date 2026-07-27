import json
import urllib.request

from config import (
    CONNECTION_ERRORS,
    GEMINI_API_KEY,
    GEMINI_API_URL,
    GEMINI_MAX_OUTPUT_TOKENS,
    MAX_COMMENTARY_LENGTH,
)


def enhance_commentary_with_llm(
    event: dict,
    base_commentary: str,
    is_friendly_event: bool | None = None,
) -> str:
    """Gemini APIでテンプレートの実況文を言い換えて生成する。未設定/失敗時はテンプレートのまま返す"""
    if not GEMINI_API_KEY:
        return base_commentary

    if is_friendly_event is True:
        bias_instruction = (
            "あなたはブルーチーム(視聴者が応援しているチーム)の専属実況として、贔屓目線で実況するアナウンサーです。"
            "この出来事はブルーチームの活躍なので、称賛や興奮を強く出してテンション高く実況してください。"
        )
    elif is_friendly_event is False:
        bias_instruction = (
            "あなたはブルーチーム(視聴者が応援しているチーム)の専属実況として、贔屓目線で実況するアナウンサーです。"
            "この出来事はレッドチーム(敵)の活躍なので、事実は伝えつつも過度に持ち上げず、"
            "ブルーチームを励ますような前向きな一言を添えてください。"
        )
    else:
        bias_instruction = (
            "あなたはブルーチーム(視聴者が応援しているチーム)を応援する実況アナウンサーです。"
            "ただしこの出来事がどちらのチームの活躍かは不明なため、有利/不利を決めつけず、"
            "淡々と事実だけを伝える実況にしてください。"
        )

    prompt = (
        f"{bias_instruction}"
        f"以下の試合イベントについて、盛り上がる実況コメントを日本語で{MAX_COMMENTARY_LENGTH}字以内の1文だけ生成してください。"
        "音声で読み上げるため長文は厳禁です。前置きや説明文は不要で、実況コメントの本文のみを返してください。\n\n"
        f"イベント種別: {event.get('EventName')}\n"
        f"イベント詳細(JSON): {json.dumps(event, ensure_ascii=False)}\n"
        f"参考(テンプレートの実況文): {base_commentary}"
    )
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS},
        }
    ).encode("utf-8")

    try:
        request = urllib.request.Request(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        text = text[:MAX_COMMENTARY_LENGTH]
        return text or base_commentary
    except (*CONNECTION_ERRORS, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Gemini APIでの実況生成に失敗しました。テンプレートの実況を使用します: {e}")
        return base_commentary
