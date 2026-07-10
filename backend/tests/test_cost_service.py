"""Tests for cost calculation service."""

from app.services import cost_service


class TestCalculateSegmentCost:
    def test_suv_default_fuel_cost(self):
        result = cost_service.calculate_segment_cost(100, "SUV")
        assert result["fuel_cost"] > 0
        assert isinstance(result["fuel_cost"], float)

    def test_sedan_lower_fuel_cost(self):
        suv = cost_service.calculate_segment_cost(100, "SUV")
        sedan = cost_service.calculate_segment_cost(100, "轿车")
        assert sedan["fuel_cost"] < suv["fuel_cost"]

    def test_toll_from_api(self):
        result = cost_service.calculate_segment_cost(100, "SUV", toll_from_api=50)
        assert result["toll_cost"] == 50

    def test_zero_distance(self):
        result = cost_service.calculate_segment_cost(0, "SUV")
        assert result["fuel_cost"] == 0


class TestCalculateRouteCost:
    def test_basic_cost_calculation(self):
        result = cost_service.calculate_route_cost(
            total_distance=500,
            days=3,
            adults=2,
            children=1,
            vehicle_type="SUV",
            scenic_count=5,
        )
        assert result["total"] > 0
        assert "fuel" in result or "fuel_cost" in result

    def test_more_people_higher_cost(self):
        small = cost_service.calculate_route_cost(
            total_distance=500, days=3, adults=2, children=0,
            vehicle_type="SUV", scenic_count=3,
        )
        large = cost_service.calculate_route_cost(
            total_distance=500, days=3, adults=4, children=2,
            vehicle_type="SUV", scenic_count=3,
        )
        assert large["total"] > small["total"]

    def test_more_days_higher_cost(self):
        short = cost_service.calculate_route_cost(
            total_distance=500, days=2, adults=2, children=0,
            vehicle_type="SUV", scenic_count=3,
        )
        long = cost_service.calculate_route_cost(
            total_distance=500, days=5, adults=2, children=0,
            vehicle_type="SUV", scenic_count=3,
        )
        assert long["total"] > short["total"]
