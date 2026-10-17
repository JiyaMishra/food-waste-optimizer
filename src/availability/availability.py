import pandas as pd

def calculate_availability(context, academic_slots=None, groups=None):
    """Estimate aggregate availability conservatively from synthetic context.

    context requires occupied_population; optional event_unavailable,
    returning_population and attendance_probability. Academic slots require
    group_id and unavailable_share (0..1); groups may provide group_sizes.
    Because event/academic person-level overlap is not available, their union
    cannot be calculated exactly; max() avoids assuming disjoint populations.
    """
    occupied = int(context.get("occupied_population", 0))
    if occupied < 0:
        raise ValueError("occupied_population must be non-negative")
    academic_unavailable = 0
    if academic_slots is not None and len(academic_slots):
        if not {"group_id", "unavailable_share"}.issubset(academic_slots.columns):
            raise ValueError("academic_slots needs group_id and unavailable_share")
        shares = pd.to_numeric(academic_slots["unavailable_share"], errors="raise")
        if shares.isna().any() or ((shares < 0) | (shares > 1)).any():
            raise ValueError("unavailable_share must be between 0 and 1")
        slots = academic_slots.assign(unavailable_share=shares)
        by_group = slots.groupby("group_id").unavailable_share.max()
        group_sizes = (groups or {}).get("group_sizes", {})
        academic_unavailable = sum(round(max(0, int(group_sizes.get(g, 0))) * share)
                                   for g, share in by_group.items())
    event_unavailable = max(0, int(context.get("event_unavailable", 0)))
    returning = max(0, int(context.get("returning_population", 0)))
    # Unknown overlap means use a conservative union estimate, not a sum.
    unavailable = min(occupied, max(academic_unavailable, event_unavailable))
    available = max(0, min(occupied, occupied - unavailable + returning))
    probability = float(context.get("attendance_probability", .65))
    if not 0 <= probability <= 1:
        raise ValueError("attendance_probability must be between 0 and 1")
    return {"occupied_population": occupied, "unavailable_population": unavailable,
            "available_population": available,
            "expected_arrivals": round(available * probability)}
