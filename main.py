import http.client
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import winsound

# ゲーム終了時の切断など、urlopen中に発生しうる通信エラー全般
_CONNECTION_ERRORS = (OSError, http.client.HTTPException)


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
_UNVERIFIED_SSL_CONTEXT = ssl._create_unverified_context()

VOICEVOX_BASE_URL = os.environ.get("VOICEVOX_BASE_URL", "http://127.0.0.1:50021")
VOICEVOX_SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "1"))  # ずんだもん(ノーマル)

POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "1.0"))

# プレイヤー識別名(summonerName/championName/riotId) -> チーム("ORDER"/"CHAOS")
player_team_map: dict[str, str] = {}


def get_active_player_riot_id() -> str | None:
    """試合中のLive Client Data APIからActiveUserのRiot ID(gameName#tagLine)を取得する"""
    try:
        with urllib.request.urlopen(
            LIVE_CLIENT_DATA_URL, context=_UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            active_player = json.load(response)
    except _CONNECTION_ERRORS as e:
        print(f"Live Client Data APIへの接続に失敗しました(試合中でない可能性があります): {e}")
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
            GAME_EVENTS_URL, context=_UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            data = json.load(response)
    except _CONNECTION_ERRORS as e:
        print(f"Live Client Data APIへの接続に失敗しました(試合中でない可能性があります): {e}")
        return None

    return data.get("Events", [])


def refresh_player_team_map() -> None:
    """AllPlayerからプレイヤーとチームの対応表を取得し、player_team_mapに保存する"""
    global player_team_map

    try:
        with urllib.request.urlopen(
            ALL_PLAYERS_URL, context=_UNVERIFIED_SSL_CONTEXT, timeout=5
        ) as response:
            all_players = json.load(response)
    except _CONNECTION_ERRORS as e:
        print(f"AllPlayerの取得に失敗しました(試合中でない可能性があります): {e}")
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


def speak(text: str, speaker: int = VOICEVOX_SPEAKER_ID) -> None:
    """VOICEVOX APIでテキストを音声合成し再生する"""
    query = urllib.parse.urlencode({"text": text, "speaker": speaker})

    try:
        audio_query_request = urllib.request.Request(
            f"{VOICEVOX_BASE_URL}/audio_query?{query}", method="POST"
        )
        with urllib.request.urlopen(audio_query_request, timeout=10) as response:
            audio_query = json.load(response)

        synthesis_request = urllib.request.Request(
            f"{VOICEVOX_BASE_URL}/synthesis?speaker={speaker}",
            data=json.dumps(audio_query).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(synthesis_request, timeout=10) as response:
            wav_data = response.read()
    except _CONNECTION_ERRORS as e:
        print(f"VOICEVOX APIへの接続に失敗しました(エンジンが起動していない可能性があります): {e}")
        return

    winsound.PlaySound(wav_data, winsound.SND_MEMORY)


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


def run_event_commentary_loop(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    """試合イベントをポーリングし、新しく発生したイベントごとに音声実況を流す"""
    last_event_id = -1
    refresh_player_team_map()
    print("イベント実況を開始します。終了するにはCtrl+Cを押してください。")

    while True:
        events = get_game_events()
        if events is None:
            # 接続失敗時は次の試合でイベントIDが0から振り直されるのに備えてリセットする
            last_event_id = -1
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        new_events = [e for e in events if e.get("EventID", -1) > last_event_id]

        for event in sorted(new_events, key=lambda e: e.get("EventID", 0)):
            commentary = build_event_commentary(event)
            if commentary:
                print(f"[{event.get('EventName')}] {commentary}")
                speak(commentary)
            last_event_id = max(last_event_id, event.get("EventID", last_event_id))

        time.sleep(poll_interval)


if __name__ == "__main__":
    while True:
        riot_id = get_active_player_riot_id()
        if riot_id:
            print(f"ActiveUserのRiot ID: {riot_id}")
            speak(f"アクティブユーザーは {riot_id} です")
            try:
                run_event_commentary_loop()
            except KeyboardInterrupt:
                print("イベント実況を終了しました。")
        else:
            print("Riot IDを取得できませんでした。")
        time.sleep(POLL_INTERVAL_SECONDS)