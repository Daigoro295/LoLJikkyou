import json
import urllib.request

from config import CONNECTION_ERRORS, GEMINI_API_KEY, GEMINI_API_URL


def enhance_commentary_with_llm(event: dict, base_commentary: str) -> str:
    """Gemini APIでテンプレートの実況文を言い換えて生成する。未設定/失敗時はテンプレートのまま返す"""
    if not GEMINI_API_KEY:
        return base_commentary

    prompt = (
        "あなたはLeague of Legendsの試合実況アナウンサーです。"
        "以下の試合イベントについて、盛り上がる短い実況コメントを日本語で1文だけ生成してください。"
        "前置きや説明文は不要で、実況コメントの本文のみを返してください。\n\n"
        f"イベント種別: {event.get('EventName')}\n"
        f"イベント詳細(JSON): {json.dumps(event, ensure_ascii=False)}\n"
        f"参考(テンプレートの実況文): {base_commentary}"
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

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
        return text or base_commentary
    except (*CONNECTION_ERRORS, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Gemini APIでの実況生成に失敗しました。テンプレートの実況を使用します: {e}")
        return base_commentary
