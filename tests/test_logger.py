"""Tests for Step 9: VIALogger service + /api/logs endpoints."""

import threading

import httpx
import pytest

from backend.main import app
from backend.services.logger import VIALogger, via_logger


# ---- Fixtures ----


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.fixture(autouse=True)
def reset_logger():
    via_logger.clear()
    yield
    via_logger.clear()


# ---- VIALogger Unit Tests ----


class TestVIALoggerLog:
    def test_log_creates_entry(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "test message")
        logs = logger.get_logs()
        assert len(logs) == 1

    def test_log_entry_has_required_fields(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "test message")
        entry = logger.get_logs()[0]
        assert "timestamp" in entry
        assert "agent" in entry
        assert "level" in entry
        assert "message" in entry
        assert "details" in entry

    def test_log_entry_timestamp_is_iso8601_utc(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "msg")
        ts = logger.get_logs()[0]["timestamp"]
        assert "T" in ts
        assert ts.endswith("Z") or ts.endswith("+00:00")

    def test_log_entry_fields_match_input(self):
        logger = VIALogger()
        logger.log("spec_agent", "WARNING", "something wrong")
        entry = logger.get_logs()[0]
        assert entry["agent"] == "spec_agent"
        assert entry["level"] == "WARNING"
        assert entry["message"] == "something wrong"

    def test_log_with_details(self):
        logger = VIALogger()
        logger.log("vision_judge", "ERROR", "failed", details={"code": 42})
        entry = logger.get_logs()[0]
        assert entry["details"] == {"code": 42}

    def test_log_without_details_is_none(self):
        logger = VIALogger()
        logger.log("system", "DEBUG", "startup")
        entry = logger.get_logs()[0]
        assert entry["details"] is None

    def test_all_valid_levels_accepted(self):
        logger = VIALogger()
        for level in ("DEBUG", "INFO", "WARNING", "ERROR"):
            logger.log("system", level, f"{level} message")
        logs = logger.get_logs()
        assert len(logs) == 4

    def test_invalid_level_raises_value_error(self):
        logger = VIALogger()
        with pytest.raises(ValueError):
            logger.log("system", "TRACE", "bad level")

    def test_empty_agent_raises_value_error(self):
        logger = VIALogger()
        with pytest.raises(ValueError):
            logger.log("", "INFO", "bad agent")


class TestVIALoggerGetLogs:
    def test_get_logs_returns_newest_first(self):
        logger = VIALogger()
        logger.log("system", "INFO", "first")
        logger.log("system", "INFO", "second")
        logger.log("system", "INFO", "third")
        logs = logger.get_logs()
        assert logs[0]["message"] == "third"
        assert logs[-1]["message"] == "first"

    def test_get_logs_filter_by_agent(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "msg1")
        logger.log("spec_agent", "INFO", "msg2")
        logger.log("orchestrator", "INFO", "msg3")
        logs = logger.get_logs(agent="orchestrator")
        assert len(logs) == 2
        assert all(e["agent"] == "orchestrator" for e in logs)

    def test_get_logs_filter_by_level(self):
        logger = VIALogger()
        logger.log("system", "INFO", "info msg")
        logger.log("system", "ERROR", "error msg")
        logger.log("system", "INFO", "another info")
        logs = logger.get_logs(level="ERROR")
        assert len(logs) == 1
        assert logs[0]["level"] == "ERROR"

    def test_get_logs_limit_restricts_results(self):
        logger = VIALogger()
        for i in range(20):
            logger.log("system", "INFO", f"msg {i}")
        logs = logger.get_logs(limit=5)
        assert len(logs) == 5

    def test_get_logs_default_limit_is_100(self):
        logger = VIALogger()
        for i in range(150):
            logger.log("system", "INFO", f"msg {i}")
        logs = logger.get_logs()
        assert len(logs) == 100

    def test_get_logs_combined_filter_agent_and_level(self):
        logger = VIALogger()
        logger.log("orchestrator", "ERROR", "orch error")
        logger.log("orchestrator", "INFO", "orch info")
        logger.log("spec_agent", "ERROR", "spec error")
        logs = logger.get_logs(agent="orchestrator", level="ERROR")
        assert len(logs) == 1
        assert logs[0]["message"] == "orch error"


class TestVIALoggerClear:
    def test_clear_removes_all_logs(self):
        logger = VIALogger()
        logger.log("system", "INFO", "a")
        logger.log("system", "INFO", "b")
        logger.clear()
        assert logger.get_logs() == []

    def test_clear_on_empty_does_not_raise(self):
        logger = VIALogger()
        logger.clear()
        assert logger.get_logs() == []


class TestVIALoggerGetAgents:
    def test_get_agents_empty_when_no_logs(self):
        logger = VIALogger()
        assert logger.get_agents() == []

    def test_get_agents_returns_unique_agents(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "a")
        logger.log("spec_agent", "INFO", "b")
        logger.log("orchestrator", "INFO", "c")
        agents = logger.get_agents()
        assert sorted(agents) == ["orchestrator", "spec_agent"]

    def test_get_agents_clears_after_clear(self):
        logger = VIALogger()
        logger.log("orchestrator", "INFO", "msg")
        logger.clear()
        assert logger.get_agents() == []


class TestVIALoggerBufferMaxSize:
    def test_buffer_drops_oldest_when_full(self):
        logger = VIALogger(max_size=5)
        for i in range(7):
            logger.log("system", "INFO", f"msg {i}")
        logs = logger.get_logs(limit=10)
        assert len(logs) == 5
        messages = [e["message"] for e in reversed(logs)]
        assert messages == ["msg 2", "msg 3", "msg 4", "msg 5", "msg 6"]

    def test_default_max_size_is_1000(self):
        logger = VIALogger()
        for i in range(1001):
            logger.log("system", "INFO", f"msg {i}")
        assert len(logger.get_logs(limit=2000)) == 1000


class TestVIALoggerThreadSafety:
    def test_concurrent_logging_does_not_corrupt_buffer(self):
        logger = VIALogger()
        errors: list[Exception] = []

        def log_many():
            try:
                for i in range(50):
                    logger.log("system", "INFO", f"thread msg {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=log_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(logger.get_logs(limit=1000)) <= 1000


class TestVIALoggerSingleton:
    def test_via_logger_is_module_level_instance(self):
        assert isinstance(via_logger, VIALogger)


# ---- API Integration Tests ----


class TestGetLogsAPI:
    @pytest.mark.anyio
    async def test_get_logs_returns_200(self, async_client):
        async with async_client as client:
            response = await client.get("/api/logs")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_get_logs_response_has_logs_and_total(self, async_client):
        async with async_client as client:
            response = await client.get("/api/logs")
        data = response.json()
        assert "logs" in data
        assert "total" in data

    @pytest.mark.anyio
    async def test_get_logs_empty_when_no_entries(self, async_client):
        async with async_client as client:
            response = await client.get("/api/logs")
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0

    @pytest.mark.anyio
    async def test_get_logs_returns_logged_entries(self, async_client):
        via_logger.log("orchestrator", "INFO", "hello")
        async with async_client as client:
            response = await client.get("/api/logs")
        data = response.json()
        assert data["total"] == 1
        assert data["logs"][0]["message"] == "hello"

    @pytest.mark.anyio
    async def test_get_logs_filter_by_agent_query_param(self, async_client):
        via_logger.log("orchestrator", "INFO", "orch msg")
        via_logger.log("spec_agent", "INFO", "spec msg")
        async with async_client as client:
            response = await client.get("/api/logs", params={"agent": "orchestrator"})
        data = response.json()
        assert data["total"] == 1
        assert data["logs"][0]["agent"] == "orchestrator"

    @pytest.mark.anyio
    async def test_get_logs_filter_by_level_query_param(self, async_client):
        via_logger.log("system", "INFO", "info msg")
        via_logger.log("system", "ERROR", "error msg")
        async with async_client as client:
            response = await client.get("/api/logs", params={"level": "ERROR"})
        data = response.json()
        assert data["total"] == 1
        assert data["logs"][0]["level"] == "ERROR"

    @pytest.mark.anyio
    async def test_get_logs_limit_query_param(self, async_client):
        for i in range(10):
            via_logger.log("system", "INFO", f"msg {i}")
        async with async_client as client:
            response = await client.get("/api/logs", params={"limit": 3})
        data = response.json()
        assert len(data["logs"]) == 3


class TestGetLogsAgentsAPI:
    @pytest.mark.anyio
    async def test_get_agents_returns_200(self, async_client):
        async with async_client as client:
            response = await client.get("/api/logs/agents")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_get_agents_returns_list(self, async_client):
        via_logger.log("orchestrator", "INFO", "a")
        via_logger.log("spec_agent", "INFO", "b")
        async with async_client as client:
            response = await client.get("/api/logs/agents")
        data = response.json()
        assert isinstance(data, list)
        assert sorted(data) == ["orchestrator", "spec_agent"]

    @pytest.mark.anyio
    async def test_get_agents_empty_when_no_logs(self, async_client):
        async with async_client as client:
            response = await client.get("/api/logs/agents")
        assert response.json() == []


class TestDeleteLogsAPI:
    @pytest.mark.anyio
    async def test_delete_logs_returns_200(self, async_client):
        async with async_client as client:
            response = await client.delete("/api/logs")
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_delete_logs_clears_all_entries(self, async_client):
        via_logger.log("system", "INFO", "a")
        via_logger.log("system", "INFO", "b")
        async with async_client as client:
            await client.delete("/api/logs")
            response = await client.get("/api/logs")
        data = response.json()
        assert data["total"] == 0
        assert data["logs"] == []
