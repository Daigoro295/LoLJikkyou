import json
import urllib.request

from config import CONNECTION_ERRORS, GEMINI_API_KEY, GEMINI_API_URL


def enhance_commentary_with_llm(
    event: dict,
    base_commentary: str,
    active_riot_id: str | None = None,
    is_friendly_event: bool | None = None,
) -> str:
    """Gemini APIでテンプレートの実況文を言い換えて生成する。未設定/失敗時はテンプレートのまま返す"""
    if not GEMINI_API_KEY:
        return base_commentary

    if active_riot_id and is_friendly_event is True:
        bias_instruction = (
            f"あなたは{active_riot_id}選手の専属実況として、贔屓目線で実況するアナウンサーです。"
            "この出来事は応援している選手側の活躍なので、称賛や興奮を強く出してテンション高く実況してください。"
        )
    elif active_riot_id and is_friendly_event is False:
        bias_instruction = (
            f"あなたは{active_riot_id}選手の専属実況として、贔屓目線で実況するアナウンサーです。"
            "この出来事は敵チームの活躍なので、事実は伝えつつも過度に持ち上げず、"
            "応援している選手側を励ますような前向きな一言を添えてください。"
        )
    elif active_riot_id:
        bias_instruction = f"あなたは{active_riot_id}選手を贔屓目線で応援する実況アナウンサーです。"
    else:
        bias_instruction = "あなたはLeague of Legendsの試合実況アナウンサーです。"

    prompt = (
        f"{bias_instruction}"
        "以下の試合イベントについて、盛り上がる短い実況コメントを日本語で生成してください。"
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
