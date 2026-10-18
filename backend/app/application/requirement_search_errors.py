from app.application.application_errors import ApplicationError


class RequirementSearchUnavailableError(ApplicationError):
    """設定された検索サービスから有効な要件を取得できない場合の例外。"""
