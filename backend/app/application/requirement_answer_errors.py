from app.application.application_errors import ApplicationError


class RequirementAnswerUnavailableError(ApplicationError):
    """ASVSを根拠とする回答を生成できない場合のapplication例外。"""
