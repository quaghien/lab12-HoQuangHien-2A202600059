# Deployment Information

## Public URL

[https://lab12-production-3c12.up.railway.app](https://lab12-production-3c12.up.railway.app)

## Platform

Railway

## Test Commands

### Health Check

```bash
curl https://lab12-production-3c12.up.railway.app/health
# Expected: {"status":"ok",...}
```

### Readiness Check

```bash
curl https://lab12-production-3c12.up.railway.app/ready
# Expected: {"status":"ready"}
```

### API Test (with authentication)

```bash
curl -X POST https://lab12-production-3c12.up.railway.app/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello, 35+46~!? "}'
```

## Environment Variables Set

- PORT
- REDIS_URL
- AGENT_API_KEY
- OPENAI_API_KEY
- LLM_MODEL
- LOG_LEVEL

## Notes

- Root path `/` returns `{"detail":"Not Found"}` by design.
- Main endpoints for validation are `/health`, `/ready`, and `POST /ask`.

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

