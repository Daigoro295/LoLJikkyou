"""Live Client Data APIのEventsに現れない状況変化を検知し、実況コメントを生成する。

Eventsはキル・タワー破壊などの離散イベントのみを含み、CS・レベル・アイテム購入と
いった地道な状況変化は含まれない。本モジュールはplayerlist/activeplayerのスナップ
ショットを前回分と比較し、節目となる変化のみをコメント化する(全ての変化を拾うと
喋りすぎるため、閾値やヒステリシスで間引く)。
"""

from config import (
    CS_MILESTONE_STEP,
    ITEM_ANNOUNCE_PRICE_THRESHOLD,
    KILL_GAP_ALERT_STEP,
    LOW_HP_RATIO,
    LOW_HP_RECOVER_RATIO,
    NOTABLE_LEVELS,
)

TEAM_LABELS = {"ORDER": "ブルー", "CHAOS": "レッド"}

_player_state: dict[str, dict] = {}
_team_kill_state = {"last_leader": None, "last_step": 0}
_low_hp_warned = False


def reset_state() -> None:
    """新しい試合の開始(または接続断からの復帰)に備えて内部状態を初期化する"""
    global _team_kill_state, _low_hp_warned

    _player_state.clear()
    _team_kill_state = {"last_leader": None, "last_step": 0}
    _low_hp_warned = False


def _display_name(player: dict) -> str:
    return player.get("championName") or player.get("summonerName") or "プレイヤー"


def _player_key(player: dict) -> str:
    riot_id_game_name = player.get("riotIdGameName")
    riot_id_tag_line = player.get("riotIdTagLine")
    if riot_id_game_name and riot_id_tag_line:
        return f"{riot_id_game_name}#{riot_id_tag_line}"
    return player.get("summonerName") or f"{player.get('championName')}_{player.get('team')}"


def detect_player_state_changes(players: list[dict]) -> list[str]:
    """プレイヤー単位の状況変化(CS到達・節目レベル・高額アイテム購入)を検知する"""
    comments: list[str] = []

    for player in players:
        key = _player_key(player)
        name = _display_name(player)
        scores = player.get("scores", {})
        level = player.get("level", 1)
        items = player.get("items", [])
        item_ids = {item.get("itemID") for item in items if not item.get("consumable")}

        state = _player_state.get(key)
        if state is None:
            # 初回観測時は基準値を記録するだけで実況はしない(途中参加時の一斉通知を防ぐ)
            _player_state[key] = {
                "cs_milestone": (scores.get("creepScore", 0) // CS_MILESTONE_STEP) * CS_MILESTONE_STEP,
                "level": level,
                "item_ids": item_ids,
            }
            continue

        cs = scores.get("creepScore", 0)
        milestone = (cs // CS_MILESTONE_STEP) * CS_MILESTONE_STEP
        if milestone > state["cs_milestone"]:
            comments.append(f"{name}がCS{milestone}に到達しました。")
            state["cs_milestone"] = milestone

        if level > state["level"]:
            for reached in range(state["level"] + 1, level + 1):
                if reached in NOTABLE_LEVELS:
                    comments.append(f"{name}がレベル{reached}になりました!")
            state["level"] = level

        new_item_ids = item_ids - state["item_ids"]
        if new_item_ids:
            for item in items:
                if item.get("itemID") in new_item_ids and (item.get("price") or 0) >= ITEM_ANNOUNCE_PRICE_THRESHOLD:
                    comments.append(f"{name}が{item.get('displayName') or 'アイテム'}を購入しました。")
            state["item_ids"] = item_ids

    comments.extend(_detect_kill_gap(players))
    return comments


def _detect_kill_gap(players: list[dict]) -> list[str]:
    """チーム間のキル差の拡大・逆転を検知する"""
    team_kills = {"ORDER": 0, "CHAOS": 0}
    for player in players:
        team = player.get("team")
        if team in team_kills:
            team_kills[team] += player.get("scores", {}).get("kills", 0)

    order_kills = team_kills["ORDER"]
    chaos_kills = team_kills["CHAOS"]
    if order_kills == 0 and chaos_kills == 0:
        return []

    if order_kills >= chaos_kills:
        leader, gap = "ORDER", order_kills - chaos_kills
    else:
        leader, gap = "CHAOS", chaos_kills - order_kills

    comments = []
    last_leader = _team_kill_state["last_leader"]

    if leader != last_leader:
        if last_leader is not None and gap > 0:
            comments.append(f"{TEAM_LABELS[leader]}チームが逆転してリードしています!")
        _team_kill_state["last_step"] = gap // KILL_GAP_ALERT_STEP
    else:
        step = gap // KILL_GAP_ALERT_STEP
        if step > _team_kill_state["last_step"]:
            comments.append(f"{TEAM_LABELS[leader]}チームが{gap}キル差でリードしています。")
            _team_kill_state["last_step"] = step

    _team_kill_state["last_leader"] = leader
    return comments


def detect_low_health(active_player: dict) -> str | None:
    """アクティブプレイヤーのHPが危険域に入った瞬間だけ警告する(エッジトリガー+ヒステリシス)"""
    global _low_hp_warned

    stats = active_player.get("championStats", {})
    health = stats.get("currentHealth")
    max_health = stats.get("maxHealth")
    if not health or not max_health:
        return None

    ratio = health / max_health

    if ratio <= LOW_HP_RATIO and not _low_hp_warned:
        _low_hp_warned = True
        return "HPが危険域です!注意してください!"

    if ratio >= LOW_HP_RECOVER_RATIO:
        _low_hp_warned = False

    return None
