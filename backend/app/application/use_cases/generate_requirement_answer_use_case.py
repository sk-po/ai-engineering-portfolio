from typing import Literal

from app.application.models.requirement_answer_dto import GeneratedRequirementAnswer
from app.application.ports.requirement_answer_generator_port import (
    RequirementAnswerGenerator,
)
from app.application.use_cases.search_requirements_use_case import SearchRequirements

NO_RELEVANT_REQUIREMENTS_ANSWER = (
    "関連するASVS要件を取得できなかったため、根拠に基づく回答を生成できませんでした。"
)


class GenerateRequirementAnswer:
    def __init__(
        self,
        search_requirements: SearchRequirements,
        answer_generator: RequirementAnswerGenerator,
    ) -> None:
        """検索と生成を順番に実行するための依存関係を保持する。

        Args:
            search_requirements: 質問に関連するASVS要件を取得するユースケース。
            answer_generator: 取得済み要件だけを根拠に回答する生成port。
        """
        self._search_requirements = search_requirements
        self._answer_generator = answer_generator

    async def execute(
        self, query: str, *, level: int | None = 2, limit: int = 5
    ) -> GeneratedRequirementAnswer:
        """関連要件を検索し、その結果を根拠として回答を生成する。

        Args:
            query: 利用者の質問。検索ユースケースが前後の空白と制約を検証する。
            level: 対象Levelの上限（1〜3）。既定は2、Noneなら全Level。
            limit: 生成へ渡す検索結果の最大件数（1〜10）。既定は5。

        Returns:
            生成回答と根拠に使用した検索結果。検索結果が空の場合は外部生成を
            呼ばず、根拠不足を示す固定回答を返す。

        Raises:
            ValueError: 検索条件が許容範囲外の場合。
            RequirementSearchUnavailableError: 要件検索を利用できない場合。
            RequirementAnswerUnavailableError: 回答生成を利用できない場合。
        """
        sources = await self._search_requirements.execute(
            query,
            level=level,
            limit=limit,
        )
        if not sources:
            return GeneratedRequirementAnswer(
                answer=NO_RELEVANT_REQUIREMENTS_ANSWER,
                sources=(),
            )
        answer = await self._answer_generator.generate(query.strip(), sources)
        return GeneratedRequirementAnswer(answer=answer, sources=sources)

    async def execute_per_level(
        self,
        query: str,
        *,
        target_level: int,
        limit_per_level: int = 5,
        search_query: str | None = None,
        response_style: Literal["standard", "security_review"] = "standard",
    ) -> GeneratedRequirementAnswer:
        """Levelごとの検索結果を根拠に、選択Levelまでの回答を生成する。

        Args:
            query: 利用者の質問。検索ユースケースが前後の空白と制約を検証する。
            target_level: L1からこのLevelまでを個別に検索する最上位Level。1〜3。
            limit_per_level: 各Levelから生成へ渡す最大根拠件数。既定は5。
            search_query: RAG検索にだけ使用する焦点語。Noneならqueryを使用する。回答生成には
                常にqueryを渡すため、検索語を短くしても機能要件の文脈は失われない。
            response_style: 回答方針。security_reviewでは具体的な機能要件に対する
                実装確認事項を優先して示す。既定はstandard。

        Returns:
            すべてのLevel別検索結果を根拠にした生成回答。根拠が空なら外部生成を呼ばない。

        Raises:
            ValueError: 検索条件が許容範囲外の場合。
            RequirementSearchUnavailableError: 要件検索を利用できない場合。
            RequirementAnswerUnavailableError: 回答生成を利用できない場合。
        """
        normalized_query = query.strip()
        retrieval_query = search_query.strip() if search_query is not None else normalized_query
        if response_style not in {"standard", "security_review"}:
            raise ValueError("response_style is invalid")
        sources = await self._search_requirements.execute_per_level(
            retrieval_query,
            target_level=target_level,
            limit_per_level=limit_per_level,
        )
        if not sources:
            return GeneratedRequirementAnswer(
                answer=NO_RELEVANT_REQUIREMENTS_ANSWER,
                sources=(),
            )
        if response_style == "security_review":
            answer = await self._answer_generator.generate(
                normalized_query, sources, response_style=response_style
            )
        else:
            answer = await self._answer_generator.generate(normalized_query, sources)
        return GeneratedRequirementAnswer(answer=answer, sources=sources)
