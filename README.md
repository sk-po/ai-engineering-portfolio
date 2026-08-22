# FDE Portfolio

Forward Deployed Engineer（FDE）への転職を目的としたポートフォリオです。

## ディレクトリ構成

```text
.
├── frontend/                  # フロントエンド
├── backend/                   # FastAPIバックエンド
├── docs/                      # 成果物ドキュメント
├── scripts/                   # 開発支援スクリプト
├── .run/                      # PyCharm共有起動設定
├── .github/workflows/         # GitHub Actions
├── .gitignore
├── README.md
├── AGENTS.md                  # 生成AI向け共通作業ルール
└── CLAUDE.md                  # Claude CodeからAGENTS.mdを参照
```

## Runtime

- Frontend: Node.js 24
- Backend: Python 3.13 / FastAPI

## Frontend

追加パッケージに依存しない、Node.js製の静的WebサーバーとHello World画面です。

```powershell
cd frontend
npm install
npm start
```

`http://127.0.0.1:3000` を開いて確認します。

```powershell
npm run lint
npm test
npm run build
```

## Backend

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

テストは次のコマンドで実行します。

```powershell
python -m unittest discover -s tests -v
```

## Git

Gitリポジトリはルートの1つだけを使用し、`frontend/` と `backend/` では初期化しません。
