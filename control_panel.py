"""LoLJikkyouの設定編集・起動をまとめて行うGUI(tkinter、追加インストール不要)"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

ENV_PATH = ".env"

# (キー, ラベル, デフォルト値, 型, 補足説明, 値を隠すか)
FIELD_GROUPS: list[tuple[str, list[tuple[str, str, str, type, str, bool]]]] = [
    (
        "音声(VOICEVOX)",
        [
            ("VOICEVOX_BASE_URL", "接続先URL", "http://127.0.0.1:50021", str, "", False),
            ("VOICEVOX_SPEAKER_ID", "話者ID", "1", int, "VOICEVOXの/speakersで確認できます", False),
            ("VOICEVOX_TIMEOUT_SECONDS", "応答タイムアウト(秒)", "15", float, "", False),
        ],
    ),
    (
        "LoLクライアント接続",
        [
            (
                "LIVE_CLIENT_BASE_URL",
                "Live Client Data APIの接続先",
                "https://127.0.0.1:2999",
                str,
                "通常は変更不要です",
                False,
            ),
            ("POLL_INTERVAL_SECONDS", "イベントのポーリング間隔(秒)", "1.0", float, "", False),
        ],
    ),
    (
        "AI実況(Gemini)",
        [
            (
                "GEMINI_API_KEY",
                "APIキー",
                "",
                str,
                "空欄の場合はLLMを使わずテンプレートの実況文をそのまま使用します",
                True,
            ),
            ("GEMINI_MODEL", "モデル名", "gemini-flash-lite-latest", str, "", False),
            ("MAX_COMMENTARY_LENGTH", "実況の最大文字数", "60", int, "音声合成のタイムアウト対策", False),
            ("GEMINI_MAX_OUTPUT_TOKENS", "Gemini出力トークン上限", "80", int, "", False),
            ("COMMENTARY_HISTORY_SIZE", "実況履歴の保持件数", "8", int, "LLMに渡す直近の実況の件数", False),
        ],
    ),
    (
        "状況変化の実況しきい値",
        [
            ("CS_MILESTONE_STEP", "CS実況の間隔", "50", int, "", False),
            ("ITEM_ANNOUNCE_PRICE_THRESHOLD", "アイテム購入実況の金額しきい値(G)", "2600", int, "", False),
            ("KILL_GAP_ALERT_STEP", "キル差実況の間隔", "3", int, "", False),
            ("LOW_HP_RATIO", "HP危険域とみなす割合", "0.25", float, "0.0〜1.0", False),
            ("LOW_HP_RECOVER_RATIO", "HP警告を解除する割合", "0.4", float, "0.0〜1.0", False),
        ],
    ),
]


def _load_existing_values() -> dict[str, str]:
    """既存の.envを読み込み、キーと値の対応を返す(見つからなければ空)"""
    values: dict[str, str] = {}
    if not os.path.exists(ENV_PATH):
        return values

    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()

    return values


def _build_env_text(values: dict[str, str]) -> str:
    """フィールド定義の順序・グループ見出しを保ったまま.envの内容を組み立てる"""
    lines: list[str] = []
    for group_name, fields in FIELD_GROUPS:
        lines.append(f"# --- {group_name} ---")
        for key, _label, _default, _kind, help_text, _secret in fields:
            if help_text:
                lines.append(f"# {help_text}")
            lines.append(f"{key}={values.get(key, '')}")
        lines.append("")
    return "\n".join(lines)


def _resolve_launch_command(extra_flag: str | None) -> tuple[list[str], str]:
    """main.py(パッケージ済みexeの場合はexe自身)を再起動するコマンドと作業ディレクトリを返す"""
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        command = [exe_path]
        cwd = os.path.dirname(exe_path)
    else:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        command = [sys.executable, script_path]
        cwd = os.path.dirname(script_path)

    if extra_flag:
        command.append(extra_flag)
    return command, cwd


class ControlPanelApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LoLJikkyou コントロールパネル")
        self.entries: dict[str, tk.StringVar] = {}
        self.show_secrets = tk.BooleanVar(value=False)
        self.current_process: subprocess.Popen | None = None

        existing = _load_existing_values()

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._secret_widgets: list[tk.Entry] = []

        for group_name, fields in FIELD_GROUPS:
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=group_name)

            for row, (key, label, default, _kind, help_text, secret) in enumerate(fields):
                ttk.Label(tab, text=label).grid(row=row * 2, column=0, sticky="w", padx=6, pady=(8, 0))

                var = tk.StringVar(value=existing.get(key, default))
                self.entries[key] = var
                entry = ttk.Entry(tab, textvariable=var, width=45, show="*" if secret else "")
                entry.grid(row=row * 2, column=1, sticky="we", padx=6, pady=(8, 0))
                if secret:
                    self._secret_widgets.append(entry)

                if help_text:
                    ttk.Label(tab, text=help_text, foreground="gray").grid(
                        row=row * 2 + 1, column=0, columnspan=2, sticky="w", padx=6
                    )

            tab.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            root, text="APIキーを表示する", variable=self.show_secrets, command=self._toggle_secrets
        ).pack(anchor="w", padx=12)

        run_frame = ttk.LabelFrame(root, text="実行")
        run_frame.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Button(run_frame, text="実況を開始", command=lambda: self._start("--run")).pack(
            side="left", padx=6, pady=6
        )
        ttk.Button(run_frame, text="テスト音声を再生", command=lambda: self._start("--test-voice")).pack(
            side="left", padx=6, pady=6
        )
        self.stop_button = ttk.Button(run_frame, text="停止", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=6, pady=6)
        self.status_label = ttk.Label(run_frame, text="● 停止中", foreground="gray")
        self.status_label.pack(side="left", padx=6)

        button_frame = ttk.Frame(root)
        button_frame.pack(fill="x", padx=8, pady=8)
        ttk.Button(button_frame, text="保存して閉じる", command=self._save).pack(side="right", padx=4)
        ttk.Button(button_frame, text="閉じる", command=root.destroy).pack(side="right", padx=4)

    def _terminate_current_process(self) -> None:
        """起動中のプロセスをツリーごと強制終了する

        パッケージ済みexe(PyInstaller onefile)は外側のプロセスが内部で実処理用の
        子プロセスを別途起動することがあり、Popen.terminate()だけでは孫プロセスが
        生き残る場合があるため、taskkill /Tでプロセスツリーごと確実に止める。
        """
        if self.current_process is None or self.current_process.poll() is not None:
            return
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)],
            capture_output=True,
        )

    def _start(self, extra_flag: str) -> None:
        """実況(または音声テスト)を別コンソールウィンドウで起動する。GUIはブロックしない"""
        if self.current_process is not None and self.current_process.poll() is None:
            if not messagebox.askyesno(
                "確認", "既に実行中のプロセスがあります。停止して新しく起動しますか?"
            ):
                return
            self._terminate_current_process()

        command, cwd = _resolve_launch_command(extra_flag)
        try:
            self.current_process = subprocess.Popen(
                command, cwd=cwd or None, creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except OSError as e:
            messagebox.showerror("起動に失敗しました", str(e))
            return

        self.stop_button.configure(state="normal")
        self.status_label.configure(text="● 実行中", foreground="green")
        self._watch_process()

    def _watch_process(self) -> None:
        """起動したプロセスが自然終了(Ctrl+Cやゲーム終了後の手動終了など)した場合に表示を戻す"""
        if self.current_process is not None and self.current_process.poll() is None:
            self.root.after(1000, self._watch_process)
        else:
            self.stop_button.configure(state="disabled")
            self.status_label.configure(text="● 停止中", foreground="gray")

    def _stop(self) -> None:
        self._terminate_current_process()
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="● 停止中", foreground="gray")

    def _toggle_secrets(self) -> None:
        show = "" if self.show_secrets.get() else "*"
        for widget in self._secret_widgets:
            widget.configure(show=show)

    def _save(self) -> None:
        values: dict[str, str] = {}

        for group_name, fields in FIELD_GROUPS:
            for key, label, _default, kind, _help_text, _secret in fields:
                raw = self.entries[key].get().strip()
                if raw:
                    try:
                        kind(raw)
                    except ValueError:
                        messagebox.showerror(
                            "入力エラー", f"「{label}」({group_name})には数値を入力してください: {raw}"
                        )
                        return
                values[key] = raw

        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write(_build_env_text(values))

        messagebox.showinfo("保存しました", "設定を.envに保存しました。反映にはLoLJikkyouの再起動が必要です。")
        self.root.destroy()


def launch() -> None:
    root = tk.Tk()
    ControlPanelApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
