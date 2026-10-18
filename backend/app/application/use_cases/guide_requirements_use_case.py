from collections.abc import Sequence

from app.application.models.guided_requirements_dto import GuidedRequirementsResult
from app.application.ports import GuidedRequirementsPlanner
from app.application.use_cases.generate_requirement_answer_use_case import (
    GenerateRequirementAnswer,
)

MAX_INTERVIEW_TURNS = 5


class GuideRequirements:
    def __init__(
        self,
        planner: GuidedRequirementsPlanner,
        generate_requirement_answer: GenerateRequirementAnswer,
    ) -> None:
        """セキュリティ確認の判断役と既存RAG回答ユースケースを保持する。

        Args:
            planner: 次の確認質問または完了を判断する生成port。
            generate_requirement_answer: 完了時にLevel別RAG回答を作るユースケース。
        """
        self._planner = planner
        self._generate_requirement_answer = generate_requirement_answer

    async def execute(
        self, feature_description: str, *, answers: Sequence[str], level: int
    ) -> GuidedRequirementsResult:
        """1ターンのセキュリティ確認を進め、必要なら根拠付きの最終回答を返す。

        Args:
            feature_description: レビュー対象の具体化済み機能要件。前後空白除去後に20文字以上必要。
            answers: これまでの利用者回答。各回答は2〜500文字で最大5件。
            level: ASVS検索に使用する最上位Level。1〜3。

        Returns:
            次の確認質問、または検索済み根拠を含む最終回答とターン番号。

        Raises:
            ValueError: 入力値が許容範囲外の場合。
            RequirementAnswerUnavailableError: 判断または最終回答の生成が利用不能な場合。
        """
        feature = feature_description.strip()
        normalized_answers = tuple(answer.strip() for answer in answers)
        if len(feature) < 20 or level not in {1, 2, 3}:
            raise ValueError("feature_description and level are invalid")
        if len(normalized_answers) > MAX_INTERVIEW_TURNS or any(
            not 2 <= len(answer) <= 500 for answer in normalized_answers
        ):
            raise ValueError("answers are invalid")

        decision = await self._planner.plan(feature, normalized_answers, level)
        if decision.action == "ask" and len(normalized_answers) < MAX_INTERVIEW_TURNS:
            return GuidedRequirementsResult(
                action="ask",
                question=decision.question,
                missing_topics=decision.missing_topics,
                answer=None,
                sources=(),
                turn=len(normalized_answers) + 1,
            )
        review_queries = (*_derive_review_queries(feature, normalized_answers), *decision.retrieval_queries)
        query = "\n".join(
            (
                "以下の機能要件をセキュリティレビューしてください。",
                feature,
                *normalized_answers,
                "回答では、機能要件から確認すべき実装上のセキュリティ事項を示してください。",
                "根拠にない認証方式や機能を列挙しないでください。",
                "検索観点:",
                *review_queries,
            )
        )
        generated = await self._generate_requirement_answer.execute_per_level(
            query,
            target_level=level,
            search_query=review_queries[0] if review_queries else feature,
            response_style="security_review",
        )
        return GuidedRequirementsResult(
            action="complete",
            question=None,
            missing_topics=decision.missing_topics,
            answer=generated.answer,
            sources=generated.sources,
            turn=len(normalized_answers),
        )


def _derive_review_queries(
    feature: str, answers: Sequence[str]
) -> tuple[str, ...]:
    """機能要件の操作語から、RAGで必ず確認すべきセキュリティ観点を補う。

    Args:
        feature: レビュー対象の具体化済み機能要件。
        answers: セキュリティ判断のために利用者が追加した回答。

    Returns:
        入力に含まれる操作に対応した日本語・英語の検索観点。該当しない場合は空タプル。

    Notes:
        これはモデルの検索観点を置き換えず、権限に関する操作がトークンやOAuthの
        一般論へ逸れることを防ぐための決定的な補助として使用する。
    """
    text = " ".join((feature, *answers))
    queries: list[str] = []
    if any(term in text for term in ("閲覧", "編集", "削除", "投稿", "会員", "権限", "所有")):
        queries.append("認可 権限 アクセス制御 所有者 データ固有 機能レベル")
    if any(term in text for term in ("画像", "ファイル", "アップロード", "添付")):
        queries.append("ファイルアップロード 拡張子 内容検証 サイズ")
    if any(term in text for term in ("口コミ", "コメント", "本文", "表示", "画面")):
        queries.append("出力エンコーディング HTML インジェクション")
    return tuple(queries)
