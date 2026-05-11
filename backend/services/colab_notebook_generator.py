"""Programmatic Jupyter notebook generator for Colab-based Ollama setup."""

import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

_ALLOWED_MODELS = {"gemma4:e4b", "gemma4:27b"}


class ColabNotebookGenerator:
    def generate(self, model: str = "gemma4:e4b") -> nbformat.NotebookNode:
        if model not in _ALLOWED_MODELS:
            raise ValueError(f"Unsupported model '{model}'. Allowed: {sorted(_ALLOWED_MODELS)}")

        cells = [
            new_markdown_cell("# VIA — Colab AI Engine Setup"),
            new_markdown_cell(
                "This notebook sets up an Ollama AI engine on Google Colab and exposes it "
                "via a cloudflared tunnel so VIA can connect remotely.\n\n"
                "**Prerequisites:** Enable a GPU runtime (Runtime → Change runtime type → T4 GPU or better) "
                "before running all cells."
            ),
            new_code_cell(
                "# Install Ollama\n"
                "!apt-get install -y zstd && curl -fsSL https://ollama.com/install.sh | sh"
            ),
            new_code_cell(
                "# Start Ollama server in background and wait for readiness\n"
                "import time, urllib.request\n"
                "\n"
                "!nohup ollama serve &\n"
                "\n"
                "for _ in range(30):\n"
                "    try:\n"
                "        urllib.request.urlopen('http://localhost:11434', timeout=2)\n"
                "        print('Ollama server is ready.')\n"
                "        break\n"
                "    except Exception:\n"
                "        time.sleep(1)\n"
                "else:\n"
                "    raise RuntimeError('Ollama server did not start in time')"
            ),
            new_code_cell(
                f"# Pull model: {model}\n"
                f"!ollama pull {model}"
            ),
            new_code_cell(
                "# Install cloudflared and start tunnel\n"
                "!curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 "
                "-o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared\n"
                "!nohup cloudflared tunnel --url http://localhost:11434 > tunnel.log 2>&1 &\n"
                "import time; time.sleep(8)\n"
                "!grep -o 'https://[^ ]*trycloudflare.com' tunnel.log || echo 'URL not found yet — run this cell again or check: !cat tunnel.log'"
            ),
            new_markdown_cell(
                "## Next step\n\n"
                "Copy the `https://*.trycloudflare.com` URL printed above, then open "
                "**VIA → Engine Settings**, switch to **Colab mode**, paste the URL, and click Save."
            ),
        ]

        nb = new_notebook(cells=cells)
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        nb.metadata["language_info"] = {"name": "python", "version": "3.11"}
        return nb
