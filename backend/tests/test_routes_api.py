"""Tests for routes API endpoints."""

from app.models.route import Route
from app.database import Base


class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["app"] == "OffroadTrip"


class TestListRoutes:
    def test_empty_list(self, client):
        resp = client.get("/api/routes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_routes(self, client, db_session):
        # Insert test routes
        for i in range(3):
            route = Route(
                share_id=f"share{i}",
                title=f"Test Route {i}",
                departure="北京",
                destination="成都",
            )
            db_session.add(route)
        db_session.commit()

        resp = client.get("/api/routes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_pagination(self, client, db_session):
        for i in range(5):
            route = Route(
                share_id=f"page{i}",
                title=f"Route {i}",
                departure="A",
                destination="B",
            )
            db_session.add(route)
        db_session.commit()

        resp = client.get("/api/routes?page=1&page_size=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        resp = client.get("/api/routes?page=2&page_size=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetRoute:
    def test_get_existing_route(self, client, db_session):
        route = Route(
            share_id="test123",
            title="Test Route",
            departure="北京",
            destination="上海",
            total_distance=1200.5,
            total_duration=14.0,
        )
        db_session.add(route)
        db_session.commit()

        resp = client.get(f"/api/routes/{route.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Route"
        assert data["departure"] == "北京"
        assert data["total_distance"] == 1200.5

    def test_get_nonexistent_route(self, client):
        resp = client.get("/api/routes/nonexistent-id")
        assert resp.status_code == 404

    def test_view_count_increment(self, client, db_session):
        route = Route(
            share_id="viewcount",
            title="VC Route",
            departure="A",
            destination="B",
            view_count=0,
        )
        db_session.add(route)
        db_session.commit()

        client.get(f"/api/routes/{route.id}")
        db_session.refresh(route)
        assert route.view_count == 1

        client.get(f"/api/routes/{route.id}")
        db_session.refresh(route)
        assert route.view_count == 2


class TestShareRoute:
    def test_share_route(self, client, db_session):
        route = Route(
            share_id="shareme",
            title="Share Route",
            departure="A",
            destination="B",
            status="draft",
        )
        db_session.add(route)
        db_session.commit()

        resp = client.post(f"/api/routes/{route.id}/share")
        assert resp.status_code == 200
        data = resp.json()
        assert "share_id" in data
        assert data["url"].startswith("/share/")

    def test_share_nonexistent_route(self, client):
        resp = client.post("/api/routes/nonexistent/share")
        assert resp.status_code == 404


class TestDeleteRoute:
    def test_delete_existing_route(self, client, db_session):
        route = Route(
            share_id="deleteme",
            title="Delete Route",
            departure="A",
            destination="B",
        )
        db_session.add(route)
        db_session.commit()
        route_id = route.id

        resp = client.delete(f"/api/routes/{route_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify deleted
        resp = client.get(f"/api/routes/{route_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent_route(self, client):
        resp = client.delete("/api/routes/nonexistent")
        assert resp.status_code == 404


class TestShareView:
    def test_get_share_by_id(self, client, db_session):
        route = Route(
            share_id="shared123",
            title="Shared Route",
            departure="A",
            destination="B",
        )
        db_session.add(route)
        db_session.commit()

        resp = client.get("/api/share/shared123")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Shared Route"

    def test_get_share_nonexistent(self, client):
        resp = client.get("/api/share/nosuchshare")
        assert resp.status_code == 404
