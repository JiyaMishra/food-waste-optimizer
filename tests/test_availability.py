import pandas as pd
import pytest
from src.availability.availability import calculate_availability

def test_overlapping_activity_is_not_double_counted():
    slots = [{"group_id": "A", "unavailable_share": .4},
             {"group_id": "A", "unavailable_share": .5}]
    result = calculate_availability({"occupied_population": 100}, pd.DataFrame(slots),
                                    {"group_sizes": {"A": 40}})
    assert result["unavailable_population"] == 20
    assert result["available_population"] == 80

def test_event_and_academic_overlap_is_not_assumed_disjoint():
    slots = pd.DataFrame([{"group_id": "A", "unavailable_share": .5}])
    result = calculate_availability({"occupied_population": 100, "event_unavailable": 30},
                                    slots, {"group_sizes": {"A": 40}})
    # Academic estimate = 20; event estimate = 30. Without person-level overlap,
    # conservatively use max(20, 30), rather than adding to 50.
    assert result["unavailable_population"] == 30
    assert result["available_population"] == 70

def test_invalid_share_rejected():
    with pytest.raises(ValueError):
        calculate_availability({"occupied_population": 10},
                                pd.DataFrame([{"group_id": "A", "unavailable_share": 1.5}]),
                                {"group_sizes": {"A": 10}})
