# AGENTS.md

このリポジトリは、FDE（Forward Deployed Engineer）転職用ポートフォリオのモノレポです。

## Repository layout

- `frontend/`: フロントエンドのソースコードとテスト
- `backend/`: FastAPIアプリケーションのソースコードとテスト
- `docs/public/`: GitHubで公開する成果物ドキュメント
- `docs/public/architecture/`: frontend/backendの設計方針の正本
- `docs/learning/`: 個人学習用の内部メモ（Git管理対象外）
- `.github/workflows/`: frontend/backendごとのCI設定
- Gitリポジトリはプロジェクトルートの1つだけとし、サブディレクトリに `.git` を作成しない

## Working rules

- 変更前に関連する既存コードとREADMEを確認する
- 既存のユーザー変更を上書きしない
- 秘密情報、APIキー、`.env`、仮想環境、依存パッケージの生成物をコミットしない
- 機能変更には、可能な範囲で自動テストを追加または更新する
- frontendとbackendの責務を分離し、共有するAPI仕様をREADMEまたは専用ドキュメントに明記する
- 実装後は対象のlint、test、buildを実行し、結果を報告する

## Mandatory architecture references

- `backend/` に関する調査・設計・実装・レビューを始める前に、`docs/public/architecture/backend.md` を必ず全文読む
- Backend APIの公開契約、ルーティング、request/response schemaを変更する前に、`docs/public/architecture/api-versioning.md` も必ず全文読む
- `frontend/` に関する調査・設計・実装・レビューを始める前に、`docs/public/architecture/frontend.md` を必ず全文読む
- レイヤー境界や依存方向を変更する場合は、実装と同じ変更内で該当する設計文書を更新する
- 設計文書と実装が矛盾する場合は、推測で解消せず、設計判断を明示してから両者を同期する

## Backend conventions

- バックエンドの初期プロジェクトはユーザーがIDEから `backend/` 配下に作成する
- Python 3.13を使用する
- Python仮想環境は `backend/.venv/` に作成する
- `docs/public/architecture/backend.md` のClean Architecture Liteと依存方向を守る
- 型ヒントを使用し、APIの入出力には明確なスキーマを定義する
- 実装後はヘルスチェック用の `GET /health` を用意する

## Frontend conventions

- フロントエンドの初期プロジェクトはユーザーがIDEから `frontend/` 配下に作成する
- フロントエンドの設計決定は `docs/public/architecture/frontend.md` に記録する
- frontend固有のコマンドは `frontend/` を作業ディレクトリとして実行する
- APIのURLなど環境依存値は環境変数で管理し、値をソースコードへ直書きしない
- アクセシビリティとレスポンシブ表示を考慮する

## Documentation

- セットアップ手順や構成を変更した場合は、同じ変更内でREADMEも更新する
- 採用担当者が短時間で目的、構成、起動方法、技術的判断を理解できる記述を優先する
- 公開する設計方針、API仕様、技術選定、運用手順は `docs/public/` に配置する
- 初歩的な学習ノート、個人向け手順、検討途中のメモは `docs/learning/` に配置する
- `docs/learning/` の内容を設計方針の正本として参照せず、採用した判断は `docs/public/` に反映する
- `docs/learning/` にも秘密情報、APIキー、個人情報を記載しない
