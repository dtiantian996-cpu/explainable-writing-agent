"""用户画像页面相关 Schema。"""

from app.schemas.assessment import ProfileDominantError
from app.schemas.common import APIModel


class ProfileResponse(APIModel):
    """长期用户画像接口响应。"""

    averageScore: float
    recentScores: list[float]
    dominantErrors: list[ProfileDominantError]
    learningPath: list[str]
    nextTargetScore: float
    summaryNarrative: str
