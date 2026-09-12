class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, field: str | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        super().__init__(message)

    def payload(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.field:
            result["field"] = self.field
        return result
