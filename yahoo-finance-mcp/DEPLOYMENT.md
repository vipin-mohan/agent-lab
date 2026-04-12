# Deploying to Hugging Face Spaces

## One-time setup

1. Create a free account at huggingface.co
2. Go to huggingface.co/new-space
3. Set Space name: `yahoo-finance-mcp`
4. Set SDK: Docker
5. Set Visibility: Public
6. Click Create Space

## Deploy via Git

```bash
git remote add space https://huggingface.co/spaces/vipinmohan/yahoo-finance-mcp
git push space main
```

## Deploy via Hugging Face CLI (alternative)

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload vipinmohan/yahoo-finance-mcp . --repo-type=space
```

## Verify deployment

- Visit: https://vipinmohan-yahoo-finance-mcp.hf.space/health
- Should return: `{"status": "ok", "server": "yahoo-finance-mcp"}`
- Space build logs available at:
  https://huggingface.co/spaces/vipinmohan/yahoo-finance-mcp/logs

## Redeploying after changes

```bash
git add .
git commit -m "your message"
git push space main
```

Hugging Face auto-rebuilds the Docker image on every push.

## Troubleshooting

- **Build fails:** check logs at the URL above
- **Port error:** confirm Dockerfile exposes 7860, not 8000
- **Server not responding:** confirm CMD uses `--port 7860`
- **Cold start:** first request after a long idle may take 5–10 seconds

## Important constraints

- `server.py` reads `PORT` from the environment: `int(os.environ.get("PORT", "8000"))` — the Dockerfile sets `ENV PORT=7860`, so this is handled automatically
- Hugging Face Spaces does not support persistent storage — this is fine since `yahoo-finance-mcp` is stateless
- Free tier CPU is shared — yfinance calls may be slightly slower than local
