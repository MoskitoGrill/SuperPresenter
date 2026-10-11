"""Confirmed immutable snapshot; draft and derived plan remain separate."""
from dataclasses import dataclass
from .layout import SlidePlan

@dataclass(frozen=True)
class ProjectionSession:
    plan: SlidePlan
    current_slide_id: str | None
    blackout: bool = False

    @classmethod
    def confirm(cls, plan: SlidePlan):
        return cls(plan, plan.slides[0].id if plan.slides else None)

    def __post_init__(self):
        if self.current_slide_id is not None and self.current_slide_id not in {s.id for s in self.plan.slides}:
            raise ValueError('Unknown current slide')
