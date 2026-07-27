MULTIKILL_NAMES = {
    2: "ダブルキル",
    3: "トリプルキル",
    4: "クアドラキル",
    5: "ペンタキル",
}


def format_unit_name(name: str | None) -> str | None:
    """タレット・ミニオンのユニット名(長いID)を読み上げ用の短い呼び名に変換する"""
    if name is None:
        return None
    if name.startswith("Turret_"):
        return "タレット"
    if name.startswith("Minion_"):
        return "ミニオン"
    return name


def build_event_commentary(event: dict) -> str | None:
    """liveclientdata/eventdataの1イベントから実況セリフを生成する"""
    event_name = event.get("EventName")
    killer = format_unit_name(event.get("KillerName"))
    stolen = event.get("Stolen") == "True"

    if event_name == "GameStart":
        return "試合開始です!"

    if event_name == "MinionsSpawning":
        return "ミニオンが出現しました!まもなくレーン戦が始まります。"

    if event_name == "FirstBrick":
        return f"{killer}が最初のタワーを破壊!ファーストタワーです!"

    if event_name == "TurretKilled":
        return f"{killer}がタワーを破壊しました!"

    if event_name == "InhibKilled":
        return f"{killer}がインヒビターを破壊!スーパーミニオンが出現します!"

    if event_name == "DragonKill":
        dragon_type = event.get("DragonType", "")
        steal_text = "スティールです!" if stolen else ""
        if dragon_type == "Elder":
            return f"{killer}がエルダードラゴンを討伐!絶大な力を手に入れました!{steal_text}"
        label = f"{dragon_type}ドラゴン" if dragon_type else "ドラゴン"
        return f"{killer}が{label}を討伐しました!{steal_text}"

    if event_name == "HeraldKill":
        steal_text = "スティールです!" if stolen else ""
        return f"{killer}がリフトヘラルドを討伐しました!{steal_text}"

    if event_name == "BaronKill":
        steal_text = "スティールです!" if stolen else ""
        return f"{killer}がバロンナシャーを討伐!チームに強力なバフが付与されます!{steal_text}"

    if event_name == "ChampionKill":
        victim = format_unit_name(event.get("VictimName"))
        return f"{killer}が{victim}を撃破!"

    if event_name == "Multikill":
        streak = event.get("KillStreak")
        kill_name = MULTIKILL_NAMES.get(streak, f"{streak}連続キル")
        return f"{killer}が{kill_name}を達成!"

    if event_name == "Ace":
        acer = event.get("Acer")
        acing_team = event.get("AcingTeam")
        return f"{acing_team}チームがエースを達成!{acer}が試合を決定づけました!"

    return None
