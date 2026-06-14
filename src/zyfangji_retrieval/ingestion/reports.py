from typing import Literal

from pydantic import BaseModel


class RowIssue(BaseModel):
    source_row: int
    code: str
    message: str
    severity: Literal["warning", "error"]
