# CleanSeam API

Quality scoring and cost-per-wear analysis for conscious consumers.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
cd app
uvicorn main:app --reload --port 8000

# Test it
curl http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"brand": "Zara", "item_type": "jeans", "price": 49.99}'
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Analyze item quality + cost-per-wear |
| `/brand/{name}` | GET | Get brand quality profile |
| `/compare` | GET | Compare multiple brands |
| `/categories` | GET | List supported categories |

## Deploy to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Init + deploy
railway init
railway up
```

## ChatGPT Action Setup

1. Deploy the API (Railway/Fly.io/Vercel)
2. Go to ChatGPT → Create a GPT
3. Add Action → Import from URL → `https://your-domain/openapi.json`
4. Configure authentication (none for MVP)

## Project Structure

```
cleanseam/
├── app/
│   └── main.py        # FastAPI application
├── openapi.yaml       # OpenAPI spec for ChatGPT
├── requirements.txt
└── README.md
```

## MVP Brand Data

Currently includes: Zara, H&M, Uniqlo, Patagonia, Shein, Levi's, Gap, COS

To add more brands, edit `BRAND_DATA` in `main.py`.

## Next Steps

1. [ ] Deploy to Railway/Fly.io
2. [ ] Register domain (cleanseam.ai)
3. [ ] Create ChatGPT Action
4. [ ] Add waitlist landing page
5. [ ] Build brand database (scrape quality data)
6. [ ] Add URL scraping for product pages
