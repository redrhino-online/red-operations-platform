"""Review policy for the Portfolio umbrella plan (pure domain).

SPEC.md section 12.5 records the canon's umbrella planning -- the Online Business
Launch Map and the one-page Bulletproof Business Plan revisited every 90 days
(canon files 00 and 01) -- as a canon gap. The canon is explicit that the plan
loses its value when it is treated as an exercise and put on the shelf (canon
file 01: "they treat it as an exercise and they put it on the shelf and they're
not redoing it every 90 days"). This policy refuses to treat an overdue plan as
current, so the revisit cadence is enforced rather than remembered.
"""

from __future__ import annotations

from datetime import date

from redops.contexts.portfolio.domain.errors import UmbrellaPlanOverdueError
from redops.contexts.portfolio.domain.value_objects import UmbrellaPlan


class UmbrellaReviewPolicy:
    """Refuses an umbrella plan whose 90-day revisit is overdue.

    The canon requires the one-page plan to be redone every 90 days and to be
    revisited on a regular basis (canon file 01). A plan whose latest recorded
    revisit scheduled its next review before the date being evaluated is stale
    and cannot be presented as the live engagement plan.
    """

    def require_current(self, plan: UmbrellaPlan, *, on: date) -> None:
        if on > plan.next_review_due:
            raise UmbrellaPlanOverdueError(
                f"umbrella plan {plan.plan_id!r} was due for its 90-day revisit "
                f"on {plan.next_review_due}, but was evaluated on {on}"
            )
