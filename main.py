import argparse
import time

from commentary import build_event_commentary
from config import POLL_INTERVAL_SECONDS
from gemini_client import enhance_commentary_with_llm
from live_client_api import get_active_player_riot_id, get_game_events, refresh_player_team_map
from voicevox_client import play_test_voice, speak


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
                commentary = enhance_commentary_with_llm(event, commentary)
                print(f"[{event.get('EventName')}] {commentary}")
                speak(commentary)
            last_event_id = max(last_event_id, event.get("EventID", last_event_id))

        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="LoL実況ツール")
    parser.add_argument(
        "--test-voice",
        action="store_true",
        help="LoLクライアント不要でVOICEVOXのテスト音声を再生して終了する",
    )
    args = parser.parse_args()

    if args.test_voice:
        print("テスト音声を繰り返し再生します。終了するにはCtrl+Cを押してください。")
        try:
            while True:
                play_test_voice()
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("テスト音声の再生を終了しました。")
        return

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


if __name__ == "__main__":
    main()
