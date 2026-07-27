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


def get_event_actor_team(event: dict) -> str | None:
    """イベントの主体(キラー等)が所属するチーム("ORDER"/"CHAOS")を取得する"""
    if event.get("EventName") == "Ace":
        acing_team = event.get("AcingTeam")
        return acing_team.upper() if acing_team else None
    return get_player_team(event.get("KillerName"))
