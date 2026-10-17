import pandas as pd

def calculate_availability(context, academic_slots=None, groups=None):
    """Estimate aggregate availability while counting overlapping activities only once.

    context requires occupied_population; optional event_unavailable and returning_population.
    academic_slots is an optional dataframe with group_id and unavailable_share (0..1).
    """
    occupied = int(context.get("occupied_population", 0))
    if occupied < 0: raise ValueError("occupied_population must be non-negative")
    unavailable = 0
    if academic_slots is not None and len(academic_slots):
        if not {"group_id","unavailable_share"}.issubset(academic_slots.columns):
            raise ValueError("academic_slots needs group_id and unavailable_share")
        # Resolve overlap by taking the maximum unavailable share per group, not summing rows.
        by_group = academic_slots.groupby("group_id").unavailable_share.max().clip(0,1)
        group_sizes = (groups or {}).get("group_sizes", {})
        unavailable = sum(round(group_sizes.get(g, 0)*share) for g, share in by_group.items())
    event_unavailable = max(0, int(context.get("event_unavailable", 0)))
    returning = max(0, int(context.get("returning_population", 0)))
    # Event overlap is not added to academic unavailability blindly; cap aggregate unavailability.
    unavailable = min(occupied, unavailable + event_unavailable)
    available = max(0, min(occupied, occupied-unavailable+returning))
    return {"occupied_population":occupied, "unavailable_population":unavailable,
            "available_population":available,
            "expected_arrivals":round(available*float(context.get("attendance_probability", .65)))}
