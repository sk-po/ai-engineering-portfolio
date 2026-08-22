# AGENTS.md

このリポジトリは、FDE（Forward Deployed Engineer）転職用ポートフォリオのモノレポです。

## Repository layout

- `frontend/`: フロントエンドのソースコードとテスト
- `backend/`: FastAPIアプリケーションのソースコードとテスト
- `.github/workflows/`: frontend/backendごとのCI設定
- Gitリポジトリはプロジェクトルートの1つだけとし、サブディレクトリに `.git` を作成しない

## Working rules

- 変更前に関連する既存コードとREADMEを確認する
- 既存のユーザー変更を上書きしない
- 秘密情報、APIキー、`.env`、仮想環境、依存パッケージの生成物をコミットしない
- 機能変更には、可能な範囲で自動テストを追加または更新する
- frontendとbackendの責務を分離し、共有するAPI仕様をREADMEまたは専用ドキュメントに明記する
- 実装後は対象のlint、test、buildを実行し、結果を報告する

## Backend conventions

- バックエンドの初期プロジェクトはユーザーがIDEから `backend/` 配下に作成する
- Python 3.13を使用する
- Python仮想環境は `backend/.venv/` に作成する
- 型ヒントを使用し、APIの入出力には明確なスキーマを定義する
- 実装後はヘルスチェック用の `GET /health` を用意する

## Frontend conventions

- フロントエンドの初期プロジェクトはユーザーがIDEから `frontend/` 配下に作成する
- frontend固有のコマンドは `frontend/` を作業ディレクトリとして実行する
- APIのURLなど環境依存値は環境変数で管理し、値をソースコードへ直書きしない
- アクセシビリティとレスポンシブ表示を考慮する

## Documentation

- セットアップ手順や構成を変更した場合は、同じ変更内でREADMEも更新する
- 採用担当者が短時間で目的、構成、起動方法、技術的判断を理解できる記述を優先する
