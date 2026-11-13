# BandScheduler

バンドや部活など、複数人の日程調整をかんたんにできるWebアプリです。

🌐 **公開URL**: https://bandscheduler-m3se.onrender.com

---

## 機能

- **Googleアカウントでログイン** — メールアドレス・パスワード不要
- **マイカレンダー** — 自分の予定を週ビューで登録・管理
- **定期予定** — 毎週の予定（バイト・授業など）を一括登録、全週に自動反映
- **グループカレンダー** — ルームを作成してURLを共有するだけでメンバーが参加可能
- **空き時間ハイライト** — メンバー全員が空いている時間帯を自動で緑表示
- **候補日設定** — 日程調整の対象日を絞り込んで表示

---

## 技術構成

| 項目 | 技術 |
|------|------|
| バックエンド | Python / Django 6.0 |
| 認証 | django-allauth（Google OAuth2） |
| データベース（本番） | PostgreSQL（Neon.tech） |
| データベース（開発） | SQLite |
| フロントエンド | HTML / CSS / JavaScript（Vanilla） |
| デプロイ | Render |
| 静的ファイル | WhiteNoise |

---

## セットアップ（ローカル開発）

```bash
git clone https://github.com/hoshina-takahashi/BandScheduler.git
cd BandScheduler
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`.env` ファイルを作成：

```
SECRET_KEY=your-secret-key
DEBUG=True
```

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## ディレクトリ構成

```
bandscheduler/
├── config/
│   ├── settings.py
│   └── urls.py
├── scheduler/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── templates/scheduler/
│       ├── base.html
│       ├── my_calendar.html
│       ├── group_calendar.html
│       ├── group_create.html
│       ├── group_list.html
│       └── recurring.html
├── templates/
│   └── account/login.html
├── requirements.txt
└── manage.py
```

---

## 開発の背景

バンドのメンバーとの練習日程調整で「全員の予定が一目でわかるツールがほしい」と思い開発しました。LINEでのやりとりや表計算ソフトでの管理が面倒だったため、URLを共有するだけで使えるシンプルなWebアプリを目指しました。

---

## 今後の予定

- Google Calendar連携
- UI改善（モバイル対応強化）
- 候補日への投票・コメント機能
