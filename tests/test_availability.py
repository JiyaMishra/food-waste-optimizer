from src.availability.availability import calculate_availability

def test_overlapping_activity_is_not_double_counted():
    slots=[{"group_id":"A","unavailable_share":.4},{"group_id":"A","unavailable_share":.5}]
    import pandas as pd
    result=calculate_availability({"occupied_population":100},pd.DataFrame(slots),{"group_sizes":{"A":40}})
    assert result["unavailable_population"] == 20
    assert result["available_population"] == 80
