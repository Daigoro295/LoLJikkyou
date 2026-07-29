# LoLJikkyou

League of Legendsの試合を、VOICEVOXによる音声とGemini APIによるAI実況でリアルタイムに実況するツールです。Live Client Data API(LoLクライアントがローカルに公開しているAPI)をポーリングし、キル・タワー破壊・ドラゴン討伐などのイベントやCS/レベルといった状況変化を検知して読み上げます。

対応OSはWindowsのみです(VOICEVOX連携に`winsound`、コンソール制御に`ctypes.windll`を使用しているため)。

## 必要なもの

- **Windows**
- **Python 3.10以降**(型ヒントに`str | None`等のPEP 604記法を使用しているため、3.10未満では動作しません)
  - パッケージ済みexe(`LoLJikkyou.exe`)を使う場合はPython不要です
- **[VOICEVOX](https://voicevox.hiroshiba.jp/)**(音声合成エンジン。起動した状態で実行してください。既定では`http://127.0.0.1:50021`に接続します)
- **League of Legends**(実況対象。試合中のみLive Client Data APIが有効になります)
- **Gemini APIキー**(任意。[Google AI Studio](https://aistudio.google.com/apikey)で無料発行可能。未設定の場合はAI実況を行わず、定型文の実況のみになります)

追加でインストールが必要なPythonパッケージはありません(標準ライブラリのみで動作します)。exe化する場合のみ`pyinstaller`が必要です。

## セットアップ

1. VOICEVOXを起動しておく
2. このリポジトリを取得し、プロジェクトフォルダで以下のいずれかの方法で設定する
   - **GUIで設定する(推奨)**: `python main.py`(またはexe)を引数なしで実行するとコントロールパネルが開くので、そこで各項目を入力して「保存して閉じる」を押す。`.env`が自動生成されます
   - **手動で設定する**: `.env.example`を`.env`という名前でコピーし、中身を編集する
3. LoLで試合を開始する

## 使い方

### 開発時(Pythonから直接実行)

```
python main.py            # コントロールパネルを開く
python main.py --run      # コントロールパネルを介さず実況ループを直接開始する
python main.py --test-voice   # LoLクライアント不要でVOICEVOXのテスト音声を繰り返し再生する
```

### コントロールパネル

引数なしで起動すると開くGUIから、以下がまとめて行えます。

- 設定項目の編集・保存(`.env`への書き込み)
- 「実況を開始」— 実況ループを別コンソールウィンドウで起動
- 「テスト音声を再生」— VOICEVOXのテスト音声を別コンソールウィンドウで再生
- 「停止」— 起動中のプロセスを停止

実況・テスト音声は別ウィンドウ(コンソール)で起動するため、ログを確認しながら実行できます。終了はそのウィンドウでCtrl+Cするか、コントロールパネルの「停止」ボタンを使ってください。

### OBSでの利用

実況中のコンソールウィンドウは`LoLJikkyou`というタイトルで開くため、OBSの「ウィンドウキャプチャ」ソースから`LoLJikkyou`を選択することで、実況ログ画面をキャプチャできます。

## 設定項目

`.env`(またはコントロールパネルのGUI)で設定できる項目です。空欄の場合は右の既定値が使われます。

### 音声(VOICEVOX)

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `VOICEVOX_BASE_URL` | `http://127.0.0.1:50021` | VOICEVOXエンジンの接続先 |
| `VOICEVOX_SPEAKER_ID` | `1`(ずんだもん・ノーマル) | 読み上げに使う話者ID。VOICEVOXの`/speakers`エンドポイントで確認できます |
| `VOICEVOX_TIMEOUT_SECONDS` | `15` | VOICEVOX APIの応答タイムアウト(秒)。長い実況文の合成が間に合わない場合は増やしてください |

### LoLクライアント接続

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `LIVE_CLIENT_BASE_URL` | `https://127.0.0.1:2999` | Live Client Data APIの接続先。通常は変更不要 |
| `POLL_INTERVAL_SECONDS` | `1.0` | イベントのポーリング間隔(秒) |

### AI実況(Gemini)

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `GEMINI_API_KEY` | (空) | Gemini APIキー。空欄の場合はLLMを使わず定型文の実況をそのまま使用します |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | 使用するGeminiモデル名 |
| `MAX_COMMENTARY_LENGTH` | `60` | 実況の最大文字数。長文化するとVOICEVOXの音声合成が間に合わずタイムアウトするための制限 |
| `GEMINI_MAX_OUTPUT_TOKENS` | `80` | Gemini APIの出力トークン上限 |
| `COMMENTARY_HISTORY_SIZE` | `8` | LLMに文脈として渡す、直近の実況履歴の保持件数 |

### 状況変化の実況しきい値

Live Client Data APIの`Events`に現れない、CS・レベル・キル差・HPなどの状況変化を実況するための閾値です。

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `CS_MILESTONE_STEP` | `50` | この数のCSに到達するごとに実況(全プレイヤー対象) |
| `KILL_GAP_ALERT_STEP` | `3` | チーム間のキル差がこの数刻みで増えるごとに実況 |
| `LOW_HP_RATIO` | `0.25` | アクティブユーザーのHPがこの割合以下になったら危険域として警告 |
| `LOW_HP_RECOVER_RATIO` | `0.4` | HP警告を解除する割合(ヒステリシス。連続警告を防ぐため) |

## exeとしてビルドする

配布・OBSでの利用を想定し、`main.py`を単体のWindows実行ファイルにパッケージ化できます。

```
pip install pyinstaller
pyinstaller --onefile --windowed --name LoLJikkyou --clean main.py
```

- `--windowed`によりコンソールなしのGUIサブシステムとしてビルドされ、`LoLJikkyou.exe`をダブルクリックするとコントロールパネルのみが表示されます(実況・テスト音声は別コンソールで起動されるため、そちらではログが見えます)
- ビルド成果物は`dist\LoLJikkyou.exe`に生成されます
- `.env`は実行時にカレントディレクトリから相対パスで読み込まれるため、`LoLJikkyou.exe`と同じフォルダに置いてください
- コードを変更した場合は再ビルドが必要です
