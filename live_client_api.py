import json
import urllib.request

from config import (
    ALL_PLAYERS_URL,
    CONNECTION_ERRORS,
    GAME_EVENTS_URL,
    LIVE_CLIENT_DATA_URL,
    UNVERIFIED_SSL_CONTEXT,
)

# プレイヤー識別名(summonerName/championName/riotId) -> チーム("ORDER"/"CHAOS")
player_team_map: dict[str, str] = {}


def get_active_player_data() -> dict | None:
    """試合中のLive Client Data APIからActiveUserの詳細データ(ステータス等)を取得する"""
    try:
        with urllib.request.urlopen(
            LIVE_CLIENT_DATA_URL, context=UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            return json.load(response)
    except CONNECTION_ERRORS as e:
        print(f"Live Client Data APIへの接続に失敗しました(試合中でない可能性があります): {e}")
        return None


def get_active_player_riot_id() -> str | None:
    """試合中のLive Client Data APIからActiveUserのRiot ID(gameName#tagLine)を取得する"""
    active_player = get_active_player_data()
    if active_player is None:
        return None

    riot_id_game_name = active_player.get("riotIdGameName")
    riot_id_tag_line = active_player.get("riotIdTagLine")
    if riot_id_game_name and riot_id_tag_line:
        return f"{riot_id_game_name}#{riot_id_tag_line}"

    if active_player.get("riotId"):
        return active_player["riotId"]

    return active_player.get("summonerName")


def get_game_events() -> list[dict] | None:
    """試合中のLive Client Data APIから発生済みイベントの一覧を取得する。接続失敗時はNoneを返す"""
    try:
        with urllib.request.urlopen(
            GAME_EVENTS_URL, context=UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            data = json.load(response)
    except CONNECTION_ERRORS as e:
        print(f"Live Client Data APIへの接続に失敗しました(試合中でない可能性があります): {e}")
        return None

    return data.get("Events", [])


def get_player_list() -> list[dict] | None:
    """試合中のLive Client Data APIから全プレイヤーの一覧(PlayerListing)を取得する"""
    try:
        with urllib.request.urlopen(
            ALL_PLAYERS_URL, context=UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            return json.load(response)
    except CONNECTION_ERRORS as e:
        print(f"AllPlayerの取得に失敗しました(試合中でない可能性があります): {e}")
        return None


def refresh_player_team_map() -> None:
    """AllPlayerからプレイヤーとチームの対応表を取得し、player_team_mapに保存する"""
    global player_team_map

    all_players = get_player_list()
    if all_players is None:
        return

    new_map: dict[str, str] = {}
    for player in all_players:
        team = player.get("team")
        if not team:
            continue

        # イベントのKillerName等はsummonerName/riotId/championNameのいずれかで来るため全て登録する
        summoner_name = player.get("summonerName")
        if summoner_name:
            new_map[summoner_name] = team

        champion_name = player.get("championName")
        if champion_name:
            new_map[champion_name] = team

        riot_id_game_name = player.get("riotIdGameName")
        riot_id_tag_line = player.get("riotIdTagLine")
        if riot_id_game_name and riot_id_tag_line:
            new_map[f"{riot_id_game_name}#{riot_id_tag_line}"] = team

    player_team_map = new_map


def get_player_team(player_name: str | None) -> str | None:
    """player_team_mapからプレイヤーの所属チーム("ORDER"/"CHAOS")を取得する"""
    if not player_name:
        return None
    return player_team_map.get(player_name)


def _structure_owner_team(structure_name: str | None) -> str | None:
    """タレット/インヒビター名(例: Turret_T1_L_03_A)から所有チームを判定する"""
    if not structure_name:
        return None
    if "_T1_" in structure_name:
        return "ORDER"
    if "_T2_" in structure_name:
        return "CHAOS"
    return None


def get_event_actor_team(event: dict) -> str | None:
    """イベントの主体(キラー等)が所属するチーム("ORDER"/"CHAOS")を取得する

    タワー/インヒビター破壊はミニオンにトドメを刺されることが多く、その場合
    KillerNameはミニオンのユニット名でplayer_team_mapに存在せず判定できない。
    破壊された構造物自身の所属チームから恩恵を受けるチーム(相手チーム)を
    逆算することで、キラーがミニオンでも正しく判定できるようにする。
    """
    event_name = event.get("EventName")

    if event_name == "Ace":
        acing_team = event.get("AcingTeam")
        return acing_team.upper() if acing_team else None

    if event_name in ("TurretKilled", "InhibKilled", "FirstBrick"):
        structure_name = event.get("TurretKilled") or event.get("InhibKilled")
        owner_team = _structure_owner_team(structure_name)
        if owner_team == "ORDER":
            return "CHAOS"
        if owner_team == "CHAOS":
            return "ORDER"

    return get_player_team(event.get("KillerName"))


def team_label(team: str | None, active_team: str | None) -> str:
    """チーム識別子("ORDER"/"CHAOS")を視聴者視点の色ラベルに変換する

    実際のORDER/CHAOSに関わらず、視聴者(アクティブプレイヤー)自身のチームは常に
    「ブルー」、相手チームは常に「レッド」と呼ぶ。自チームが判定できない場合のみ、
    ゲーム本来の割り当て(ORDER=ブルー/CHAOS=レッド)にフォールバックする。
    """
    if not team:
        return "不明"
    if active_team is None:
        return "ブルー" if team == "ORDER" else "レッド"
    return "ブルー" if team == active_team else "レッド"
