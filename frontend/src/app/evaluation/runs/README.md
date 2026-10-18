# 評価runスナップショット（画面同梱）

オフライン評価の結果を画面表示するための**公開用スナップショット**を置く。評価の実行はローカルで行い、公開すると決めたrunだけをここへ昇格する。

## ファイル

- `*.json`: 公開するrunの実測結果（`backend/scripts/evaluate_*` の出力から昇格したもの）
- `manifest.json`: 公開run一覧の**正本**（`id` / `label` / `file`）。並び順が画面の表示順
- `manifest.js`: `manifest.json` から**自動生成**。静的importを保つための生成物。手で編集しない
- `index.js`: `manifest.js` を読み、検索専用 / RAGAS統合の両スキーマを共通形へ正規化する

## 更新手順（ローカル実行 → 同梱）

1. ローカルで評価を実行する（クラウドにジョブは置かない）。

   ```powershell
   docker compose exec backend python scripts/evaluate_ragas.py --concurrency 1
   # 出力: backend/test-results/ragas-evaluation-<timestamp>.json
   ```

2. 公開すると決めたrunを昇格する（`frontend` を作業ディレクトリで）。

   ```powershell
   npm run publish:eval -- `
     --source ../backend/test-results/ragas-evaluation-<timestamp>.json `
     --id ragas-azure-51 `
     --label "Azure + RAGAS（51件・検索+生成）"
   ```

   同じ `--id` を指定すると既存スナップショットを差し替える。新規IDは一覧の先頭へ追加される。

3. 生成された `*.json` / `manifest.json` / `manifest.js` の差分をコミットする。

## 方針

- 表示は**ビルド時同梱**。数値はコミットに固定され再現性を持つ。
- `backend/test-results/` は評価の生出力（管理対象外）。ここには**公開すると選んだ確定版だけ**を置く。
- 頻繁に更新・蓄積するデータ（オンライン評価など）が出たら、同梱ではなくストア（Blob/RDB）へ移す。
