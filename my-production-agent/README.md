# Full Source Code - Lab 06 Complete (60 points)

Production-ready AI agent cho Part 6, theo đúng trọng tâm bạn chốt:

- REST API trả lời câu hỏi
- Conversation history lưu trong Redis (stateless)
- API key auth
- Rate limit `10 req/min/user`
- Cost guard `$10/tháng/user`
- Health + readiness
- Graceful shutdown
- Structured JSON logging
- Docker multi-stage
- Deploy Railway
- Model mặc định: `gpt-5.4-mini`

## Phân biệt API keys (quan trọng)

- `AGENT_API_KEY`: key bảo vệ endpoint `/ask` của chính app bạn. Client phải gửi header `X-API-Key` để gọi API.
- `OPENAI_API_KEY`: key để app gọi OpenAI API thật.
- Logic hiện tại: có `OPENAI_API_KEY` thì gọi OpenAI thật, thiếu key thì fallback về `utils/mock_llm.py`.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Nginx (LB)    │
└──────┬──────────┘
       │
       ├─────────┬─────────┐
       ▼         ▼         ▼
   ┌──────┐  ┌──────┐  ┌──────┐
   │Agent1│  │Agent2│  │Agent3│
   └───┬──┘  └───┬──┘  └───┬──┘
       │         │         │
       └─────────┴─────────┘
                 │
                 ▼
           ┌──────────┐
           │  Redis   │
           └──────────┘
```

## Cấu trúc

```
my-production-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   └── cost_guard.py
├── utils/
│   └── mock_llm.py
├── nginx/
│   └── nginx.conf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
├── railway.toml
└── README.md
```

## Chạy local với 3 agent sau Nginx

```bash
cp .env.example .env
docker compose up --build --scale agent=3
```

Luồng public đi qua Nginx ở cổng `80`, nên test bằng `http://localhost`:

```bash
curl http://localhost/health
curl http://localhost/ready

curl -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key-123" \
  -d '{"user_id":"user1","question":"Xin chào agent"}'
```

Streaming (optional):

```bash
curl -N -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key-123" \
  -d '{"user_id":"user1","question":"stream thử","stream":true}'
```

## Tạo Redis trong cùng project

Nếu chưa có Redis:

railway add

Rồi chọn:

Database → Redis

Hoặc dùng CLI trực tiếp:

railway add -d redis

Railway hỗ trợ thêm database Redis bằng railway add.

## Deploy Railway

```bash
railway login
railway init
railway link
railway add #-> chọn Empty Service -> / Nếu chọn db thì chọn redis
railway service
railway variables set AGENT_API_KEY=your-secret-key
railway variables set REDIS_URL=redis://<your-redis-url>
railway variables set OPENAI_API_KEY=sk-...   # bắt buộc nếu muốn dùng GPT thật
railway variables set LLM_MODEL=gpt-5.4-mini

railway variables

#railway up
railway up --verbose

railway domain
railway status
```

