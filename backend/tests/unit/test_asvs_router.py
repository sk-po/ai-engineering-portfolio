import unittest
from unittest.mock import AsyncMock, Mock

from app.application.models import GeneratedRequirementAnswer
from app.application.use_cases import GenerateRequirementAnswer, SearchRequirements
from app.presentation.api.routers.asvs_router import (
    generate_requirement_answer,
    search_requirements,
)
from app.presentation.api.schemas.asvs_schema import (
    RequirementAnswerRequest,
    RequirementSearchRequest,
)


class SearchRequirementsRouterTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_awaits_asynchronous_use_case(self) -> None:
        """非同期ユースケースをawaitして検索結果をレスポンスへ変換することを確認する。"""
        use_case = Mock(spec=SearchRequirements)
        use_case.execute = AsyncMock(return_value=())
        request = RequirementSearchRequest(query="認証")

        response = await search_requirements(request, use_case)

        use_case.execute.assert_awaited_once_with(
            "認証",
            level=2,
            limit=5,
        )
        self.assertEqual(response.results, [])

    async def test_awaits_answer_use_case(self) -> None:
        """回答生成ユースケースをawaitし、公開レスポンスへ変換する。"""
        use_case = Mock(spec=GenerateRequirementAnswer)
        use_case.execute = AsyncMock(
            return_value=GeneratedRequirementAnswer(answer="根拠不足です。", sources=())
        )
        request = RequirementAnswerRequest(query="認証")

        response = await generate_requirement_answer(request, use_case)

        use_case.execute.assert_awaited_once_with("認証", level=2, limit=5)
        self.assertEqual(response.answer, "根拠不足です。")
        self.assertEqual(response.sources, [])
