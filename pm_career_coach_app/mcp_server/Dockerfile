# PM Career Coach — MCP Server
# Deploys on Hugging Face Spaces (Docker SDK) on port 7860.
#
# Build context: pm_career_coach_app/   (one directory above this file)
# Build command (from pm_career_coach_app/):
#   docker build -f mcp_server/Dockerfile -t pm-coach-mcp .
#
# Run:
#   docker run --rm -p 7860:7860 \
#     -e MCP_BEARER_TOKEN=your-secret-token \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     -e PINECONE_API_KEY=pcsk-... \
#     pm-coach-mcp

FROM python:3.11-slim

# HF Spaces requires the app to run as a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first (layer-cached unless requirements change)
COPY mcp_server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy shared core library and MCP server package
COPY core/ ./core/
COPY mcp_server/ ./mcp_server/

USER appuser

EXPOSE 7860

# Run with uvicorn; workers=1 keeps the in-process singleton cache coherent.
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
