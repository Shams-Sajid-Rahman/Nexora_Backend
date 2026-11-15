"""Report schemas."""
from pydantic import BaseModel


class ReportExportCreate(BaseModel):
    report_type: str
    format: str = "csv"
