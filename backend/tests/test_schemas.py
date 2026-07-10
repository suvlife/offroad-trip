"""Tests for Pydantic request/response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.route import GenerateRequest


class TestGenerateRequest:
    def test_valid_request(self):
        req = GenerateRequest(departure="北京", destination="成都")
        assert req.departure == "北京"
        assert req.destination == "成都"
        assert req.days == 3
        assert req.adults == 2

    def test_departure_too_short(self):
        with pytest.raises(ValidationError, match="at least 2 characters"):
            GenerateRequest(departure="a", destination="成都")

    def test_destination_too_short(self):
        with pytest.raises(ValidationError, match="at least 2 characters"):
            GenerateRequest(departure="北京", destination="b")

    def test_departure_too_long(self):
        with pytest.raises(ValidationError, match="at most 50"):
            GenerateRequest(departure="a" * 51, destination="成都")

    def test_days_out_of_range(self):
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", days=0)
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", days=31)

    def test_adults_out_of_range(self):
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", adults=0)
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", adults=21)

    def test_children_out_of_range(self):
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", children=-1)
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", children=11)

    def test_budget_out_of_range(self):
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", budget=-1)
        with pytest.raises(ValidationError):
            GenerateRequest(departure="北京", destination="成都", budget=1000001)

    def test_city_name_sanitization(self):
        req = GenerateRequest(departure="北京!", destination="成都@#")
        assert req.departure == "北京"
        assert req.destination == "成都"

    def test_city_name_with_spaces(self):
        req = GenerateRequest(departure="北 京", destination="成 都")
        assert req.departure == "北 京"
        assert req.destination == "成 都"

    def test_city_name_english(self):
        req = GenerateRequest(departure="Beijing", destination="Chengdu")
        assert req.departure == "Beijing"
        assert req.destination == "Chengdu"

    def test_city_name_all_special_chars_becomes_empty(self):
        with pytest.raises(ValidationError, match="不能为空"):
            GenerateRequest(departure="!!!", destination="成都")
