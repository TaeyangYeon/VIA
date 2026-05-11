"""Tests for Step 42: Colab Setup Notebook Generator and download endpoint."""

import pytest
import nbformat
import httpx

from backend.main import app
from backend.services.colab_notebook_generator import ColabNotebookGenerator


# ============================================================
# ColabNotebookGenerator unit tests
# ============================================================


class TestColabNotebookGeneratorStructure:
    def test_generate_returns_notebook_node(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        assert isinstance(nb, nbformat.NotebookNode)

    def test_default_model_is_gemma4_e4b(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        source = "\n".join(cell.source for cell in nb.cells if cell.cell_type == "code")
        assert "gemma4:e4b" in source

    def test_model_name_appears_in_pull_cell(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate(model="gemma4:27b")
        pull_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "ollama pull" in c.source
        )
        assert "gemma4:27b" in pull_cell.source

    def test_notebook_has_correct_cell_count(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        # 2 markdown + 4 code + 1 final markdown = 7 cells
        assert len(nb.cells) == 7

    def test_cell_types_are_correct(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        expected = ["markdown", "markdown", "code", "code", "code", "code", "markdown"]
        actual = [c.cell_type for c in nb.cells]
        assert actual == expected

    def test_title_cell_contains_via(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        title_cell = nb.cells[0]
        assert title_cell.cell_type == "markdown"
        assert "VIA" in title_cell.source

    def test_title_cell_is_correct_heading(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        assert "VIA — Colab AI Engine Setup" in nb.cells[0].source

    def test_ollama_install_cell_contains_curl_and_ollama(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        install_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "install.sh" in c.source
        )
        assert "curl" in install_cell.source
        assert "ollama" in install_cell.source

    def test_ollama_install_cell_contains_zstd(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        install_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "install.sh" in c.source
        )
        assert "apt-get install -y zstd" in install_cell.source

    def test_server_start_cell_contains_ollama_serve(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        serve_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "ollama serve" in c.source
        )
        assert "ollama serve" in serve_cell.source

    def test_model_pull_cell_contains_default_model(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        pull_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "ollama pull" in c.source
        )
        assert "gemma4:e4b" in pull_cell.source

    def test_cloudflared_cell_contains_cloudflared_and_tunnel(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        cf_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "cloudflared" in c.source
        )
        assert "cloudflared" in cf_cell.source
        assert "tunnel" in cf_cell.source

    def test_cloudflared_cell_uses_tunnel_log(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        cf_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "cloudflared" in c.source
        )
        assert "tunnel.log" in cf_cell.source

    def test_cloudflared_cell_extracts_url_via_grep(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        cf_cell = next(
            c for c in nb.cells
            if c.cell_type == "code" and "cloudflared" in c.source
        )
        assert "grep" in cf_cell.source
        assert "trycloudflare.com" in cf_cell.source

    def test_invalid_model_raises_value_error(self):
        gen = ColabNotebookGenerator()
        with pytest.raises(ValueError):
            gen.generate(model="invalid-model")

    def test_gemma4_27b_model_works(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate(model="gemma4:27b")
        assert isinstance(nb, nbformat.NotebookNode)
        source = "\n".join(cell.source for cell in nb.cells if cell.cell_type == "code")
        assert "gemma4:27b" in source

    def test_notebook_is_valid_per_nbformat_validate(self):
        gen = ColabNotebookGenerator()
        nb = gen.generate()
        nbformat.validate(nb)  # raises nbformat.ValidationError if invalid


# ============================================================
# GET /api/engine/setup-notebook endpoint tests
# ============================================================


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


class TestSetupNotebookEndpoint:
    @pytest.mark.anyio
    async def test_returns_200(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_content_type_is_ipynb(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        assert "application/json" in resp.headers["content-type"]

    @pytest.mark.anyio
    async def test_content_disposition_contains_setup_notebook(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        assert "setup_notebook" in resp.headers["content-disposition"]

    @pytest.mark.anyio
    async def test_content_disposition_is_attachment(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        assert "attachment" in resp.headers["content-disposition"]

    @pytest.mark.anyio
    async def test_default_model_parameter_works(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        assert resp.status_code == 200
        nb = resp.json()
        sources = "\n".join(c["source"] for c in nb["cells"] if c["cell_type"] == "code")
        assert "gemma4:e4b" in sources

    @pytest.mark.anyio
    async def test_custom_model_gemma4_27b_works(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook?model=gemma4%3A27b")
        assert resp.status_code == 200
        nb = resp.json()
        sources = "\n".join(c["source"] for c in nb["cells"] if c["cell_type"] == "code")
        assert "gemma4:27b" in sources

    @pytest.mark.anyio
    async def test_invalid_model_returns_400(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook?model=bad-model")
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_response_body_is_valid_json_notebook(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook")
        nb_dict = resp.json()
        assert "cells" in nb_dict
        assert "nbformat" in nb_dict

    @pytest.mark.anyio
    async def test_notebook_contains_model_name_in_cells(self, async_client):
        async with async_client as client:
            resp = await client.get("/api/engine/setup-notebook?model=gemma4%3A27b")
        nb_dict = resp.json()
        sources = "\n".join(c["source"] for c in nb_dict["cells"])
        assert "gemma4:27b" in sources
