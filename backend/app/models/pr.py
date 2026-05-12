from pydantic import BaseModel


class PRItem(BaseModel):
    number: int
    title: str
    url: str
    created_at: str
    merged_at: str | None
    state: str


class PRListResponse(BaseModel):
    prs: list[PRItem]
    total: int
    page: int
    per_page: int
