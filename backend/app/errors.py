from fastapi import HTTPException, status


def domain_error(http_status: int, code: str, message: str) -> HTTPException:
    """Доменная ошибка в формате контракта: {"detail": {"code": ..., "message": ...}}."""
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def not_found(code: str, message: str) -> HTTPException:
    return domain_error(status.HTTP_404_NOT_FOUND, code, message)
