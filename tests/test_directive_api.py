"""Tests for Step 8: Agent Directive API."""

import pytest
import httpx

from backend.main import app
from backend.services.directive_store import directive_store


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def reset_directives():
    directive_store.reset()
    yield
    directive_store.reset()


# ---- DirectiveStore Unit Tests ----


class TestDirectiveStore:
    def test_initial_state_all_none(self):
        directive_store.reset()
        result = directive_store.get()
        assert result["orchestrator"] is None
        assert result["spec"] is None
        assert result["image_analysis"] is None
        assert result["pipeline_composer"] is None
        assert result["vision_judge"] is None
        assert result["inspection_plan"] is None
        assert result["algorithm_coder"] is None
        assert result["test"] is None

    def test_update_single_agent(self):
        directive_store.update("orchestrator", "focus on speed")
        result = directive_store.get()
        assert result["orchestrator"] == "focus on speed"

    def test_update_leaves_others_none(self):
        directive_store.update("spec", "prioritize accuracy")
        result = directive_store.get()
        assert result["spec"] == "prioritize accuracy"
        assert result["orchestrator"] is None

    def test_save_full_directives(self):
        data = {"orchestrator": "go fast", "spec": None, "image_analysis": "be precise"}
        directive_store.save(data)
        result = directive_store.get()
        assert result["orchestrator"] == "go fast"
        assert result["image_analysis"] == "be precise"

    def test_reset_clears_all_to_none(self):
        directive_store.update("orchestrator", "some directive")
        directive_store.reset()
        result = directive_store.get()
        assert result["orchestrator"] is None

    def test_update_nonexistent_agent_raises(self):
        with pytest.raises((ValueError, KeyError)):
            directive_store.update("nonexistent_agent", "value")


# ---- POST /api/directives ----


class TestPostDirectives:
    @pytest.mark.anyio
    async def test_post_empty_directives_returns_200(self, async_client):
        payload = {}
        async with async_client as client:
            response = await client.post("/api/directives", json=payload)
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_post_directives_saves_to_store(self, async_client):
        payload = {"orchestrator": "prioritize latency"}
        async with async_client as client:
            await client.post("/api/directives", json=payload)
        result = directive_store.get()
        assert result["orchestrator"] == "prioritize latency"

    @pytest.mark.anyio
    async def test_post_directives_response_includes_all_fields(self, async_client):
        payload = {"orchestrator": "go fast"}
        async with async_client as client:
            response = await client.post("/api/directives", json=payload)
        data = response.json()
        assert "orchestrator" in data
        assert "spec" in data
        assert "image_analysis" in data
        assert "pipeline_composer" in data
        assert "vision_judge" in data
        assert "inspection_plan" in data
        assert "algorithm_coder" in data
        assert "test" in data

    @pytest.mark.anyio
    async def test_post_directives_unspecified_fields_remain_none(self, async_client):
        payload = {"orchestrator": "go fast"}
        async with async_client as client:
            response = await client.post("/api/directives", json=payload)
        data = response.json()
        assert data["spec"] is None
        assert data["image_analysis"] is None

    @pytest.mark.anyio
    async def test_post_all_directives(self, async_client):
        payload = {
            "orchestrator": "d1",
            "spec": "d2",
            "image_analysis": "d3",
            "pipeline_composer": "d4",
            "vision_judge": "d5",
            "inspection_plan": "d6",
            "algorithm_coder": "d7",
            "test": "d8",
        }
        async with async_client as client:
            response = await client.post("/api/directives", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["orchestrator"] == "d1"
        assert data["test"] == "d8"

    @pytest.mark.anyio
    async def test_post_unknown_field_ignored_or_422(self, async_client):
        payload = {"nonexistent_agent": "value"}
        async with async_client as client:
            response = await client.post("/api/directives", json=payload)
        # Pydantic v2 with model_config extra="ignore" returns 200; extra="forbid" returns 422
        assert response.status_code in (200, 422)


# ---- GET /api/directives ----


class TestGetDirectives:
    @pytest.mark.anyio
    async def test_get_directives_returns_200(self, async_client):
        async with async_client as client:
            response = await client.get("/api/directives")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_get_directives_initially_all_none(self, async_client):
        async with async_client as client:
            response = await client.get("/api/directives")
        data = response.json()
        assert data["orchestrator"] is None
        assert data["spec"] is None

    @pytest.mark.anyio
    async def test_get_directives_returns_saved_values(self, async_client):
        payload = {"spec": "minimize false negatives"}
        async with async_client as client:
            await client.post("/api/directives", json=payload)
            response = await client.get("/api/directives")
        data = response.json()
        assert data["spec"] == "minimize false negatives"


# ---- PUT /api/directives/{agent_name} ----


class TestPutDirective:
    @pytest.mark.anyio
    async def test_put_updates_single_agent_directive(self, async_client):
        async with async_client as client:
            response = await client.put(
                "/api/directives/orchestrator",
                json={"directive": "be aggressive"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["orchestrator"] == "be aggressive"

    @pytest.mark.anyio
    async def test_put_leaves_other_agents_unchanged(self, async_client):
        directive_store.update("spec", "original spec directive")
        async with async_client as client:
            await client.put(
                "/api/directives/orchestrator",
                json={"directive": "new orchestrator directive"},
            )
        result = directive_store.get()
        assert result["spec"] == "original spec directive"

    @pytest.mark.anyio
    async def test_put_nonexistent_agent_returns_404(self, async_client):
        async with async_client as client:
            response = await client.put(
                "/api/directives/nonexistent_agent",
                json={"directive": "value"},
            )
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_put_clears_directive_with_none(self, async_client):
        directive_store.update("orchestrator", "some value")
        async with async_client as client:
            response = await client.put(
                "/api/directives/orchestrator",
                json={"directive": None},
            )
        assert response.status_code == 200
        assert directive_store.get()["orchestrator"] is None

    @pytest.mark.anyio
    async def test_put_all_valid_agent_names(self, async_client):
        valid_agents = [
            "orchestrator", "spec", "image_analysis", "pipeline_composer",
            "vision_judge", "inspection_plan", "algorithm_coder", "test",
        ]
        async with async_client as client:
            for agent in valid_agents:
                response = await client.put(
                    f"/api/directives/{agent}",
                    json={"directive": f"directive for {agent}"},
                )
                assert response.status_code == 200


# ---- DELETE /api/directives ----


class TestDeleteDirectives:
    @pytest.mark.anyio
    async def test_delete_resets_all_directives_to_none(self, async_client):
        directive_store.update("orchestrator", "some value")
        directive_store.update("spec", "another value")
        async with async_client as client:
            response = await client.delete("/api/directives")
        assert response.status_code == 200
        result = directive_store.get()
        assert result["orchestrator"] is None
        assert result["spec"] is None

    @pytest.mark.anyio
    async def test_delete_returns_all_none_directives(self, async_client):
        directive_store.update("orchestrator", "something")
        async with async_client as client:
            response = await client.delete("/api/directives")
        data = response.json()
        assert data["orchestrator"] is None
        assert data["spec"] is None

    @pytest.mark.anyio
    async def test_delete_on_empty_directives_returns_200(self, async_client):
        async with async_client as client:
            response = await client.delete("/api/directives")
        assert response.status_code == 200
