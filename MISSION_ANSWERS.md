# Day 12 Lab - Mission Answers

> **Student Name:** Hồ Quang Hiển
> **Student ID:** 2A202600059
> **Date:** 17/04/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Phân tích file `01-localhost-vs-production/develop/app.py`:

1. **Hardcoded secrets** — API Key và Database URL ghi thẳng vào code (dòng 17-18): `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`. Nếu push lên GitHub, secrets bị lộ ngay lập tức.
2. **Không có Config Management** — Biến `DEBUG = True` cứng trong code. Muốn thay đổi phải sửa code, không thể điều chỉnh qua environment variable.
3. **Logging bằng `print()` thay vì structured logging** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`. Vừa log ra secret, vừa không có timestamp/log level để phân tích.
4. **Không có `/health` endpoint** — Platform không biết app còn sống hay đã crash để tự động restart Container.
5. **`host="localhost"` thay vì `0.0.0.0`** — Container chỉ lắng nghe trên loopback, không nhận được traffic từ bên ngoài.
6. **`reload=True` trong production** — File watcher làm tăng CPU, không ổn định trong môi trường production.

---

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---|---|---|---|
| Config | Hardcode trong code | Đọc từ `os.getenv()` / env file | Secrets không commit vào git; linh hoạt giữa các môi trường |
| Logging | `print(f"[DEBUG]...")` | Structured JSON với log level | Dễ lọc, tổng hợp log trên Cloud (ELK/Datadog) |
| Health Check | Không có | `GET /health` + `GET /ready` | Platform biết khi nào restart Container tự động |
| Host binding | `localhost` | `0.0.0.0` | Container nhận được traffic từ bên ngoài |
| Auth | Không có | API Key header `X-API-Key` | Chặn truy cập trái phép |
| Rate Limiting | Không có | 20 req/min sliding window | Tránh bị DDoS / lạm dụng tài nguyên |
| Error handling | Không có — 500 thô | HTTPException có message rõ ràng | UX tốt hơn; không lộ stack trace |
| Graceful shutdown | Không | SIGTERM handler + lifespan | Không mất request đang xử lý khi restart |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

Phân tích `02-docker/develop/Dockerfile`:

1. **Base image:** `python:3.11` — Full Python distribution (~1GB), bao gồm toàn bộ công cụ build
2. **Working directory:** `/app`
3. **Cài dependencies:** `RUN pip install --no-cache-dir -r requirements.txt`
4. **CMD:** `["python", "app.py"]` — Chạy trực tiếp file Python, không dùng uvicorn worker
5. **HEALTHCHECK:** ❌ Không có — Platform không thể tự kiểm tra sức khoẻ Container
6. **Non-root user:** ❌ Không có — Container chạy bằng quyền root, vi phạm security best practice

---

### Exercise 2.3: Image size comparison

Số liệu **thực đo** bằng lệnh `docker images | grep agent` trên máy:

- **Develop** (`agent-develop:latest`): **1,660 MB** — `python:3.11` full + single-stage
- **Production** (`production-agent:latest`): **236 MB** — `python:3.11-slim` + multi-stage
- **Difference:** giảm **85.8%** (1,424 MB nhỏ hơn)

**Lý giải:** `python:3.11` full image chứa hàng GB công cụ build (gcc, header C, pip cache...). Multi-stage Build tách riêng Stage Builder (cài deps) và Stage Runtime (chỉ copy output). Image cuối không còn build tools, chỉ giữ Python runtime và site-packages đã compile.

```
Stage 1 (Builder)          Stage 2 (Runtime)
─────────────────          ─────────────────
python:3.11-slim           python:3.11-slim
+ gcc, libpq-dev    ──►    + .local/lib/ (packages only)
+ pip install              + source code
= ~800MB tạm thời          = 236MB final ✅
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://lab1-production-7fdb.up.railway.app
- **Platform:** Railway (Nixpacks v1.38.0 auto-detect Python)

**Test URL public:**
```bash
curl https://lab1-production-7fdb.up.railway.app/health
# Kết quả: {"message":"AI Agent running on Railway!","docs":"/docs","health":"/health"}
```

**Screenshot — Service đang chạy trên Railway:**

![Screenshot](./mission_answers_Cloud_Deployment.png)

---

## Part 4: API Security

### Exercise 4.1–4.3: Test results

*(Dưới đây là input đã chạy và output copy từ terminal. Cảnh báo `libcurl.so.4: no version information available` do Miniconda — có thể bỏ qua, không đổi mã HTTP.)*

#### Develop — `04-api-gateway/develop/` (port **8001**, API Key)

**Có API Key đúng → 200**

```text
curl -sS -X POST "http://localhost:8001/ask?question=hello" -H "X-API-Key: my-secret-key"
{"question":"hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

**Không gửi API Key → 401**

```text
curl -sS -i -X POST "http://localhost:8001/ask?question=hello"
HTTP/1.1 401 Unauthorized
date: Fri, 17 Apr 2026 15:27:33 GMT
server: uvicorn
content-length: 67
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

**API Key sai → 403**

```text
curl -sS -i -X POST "http://localhost:8001/ask?question=hello" -H "X-API-Key: wrong-key"
HTTP/1.1 403 Forbidden
date: Fri, 17 Apr 2026 15:27:44 GMT
server: uvicorn
content-length: 29
content-type: application/json
```

#### Production — `04-api-gateway/production/` (port **8002**, JWT)

**Đăng nhập lấy token (student) → 200**

```text
curl -sS -X POST "http://localhost:8002/auth/token" -H "Content-Type: application/json" -d '{"username":"student","password":"demo123"}'
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0NDAwODEsImV4cCI6MTc3NjQ0MzY4MX0.wchiJxghFpKAUXLFTDHbb0r1ZKF5eozUtyLCe44pzgI","token_type":"bearer","expires_in_minutes":60,"hint":"Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."}
```

**Gọi `/ask` có Bearer → 200**

```text
TOKEN='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0NDAwODEsImV4cCI6MTc3NjQ0MzY4MX0.wchiJxghFpKAUXLFTDHbb0r1ZKF5eozUtyLCe44pzgI'
curl -sS -X POST "http://localhost:8002/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"what is docker?"}'
{"question":"what is docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

**Không gửi Bearer → 401**

```text
curl -sS -i -X POST "http://localhost:8002/ask" -H "Content-Type: application/json" -d '{"question":"hi"}'
HTTP/1.1 401 Unauthorized
date: Fri, 17 Apr 2026 15:36:21 GMT
server: uvicorn
www-authenticate: Bearer
content-length: 76
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
```

**Nhầm port (ví dụ 8000 thay vì 8002) — cùng JWT, vòng 15 lần → toàn 401**

```text
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0NDAwODEsImV4cCI6MTc3NjQ0MzY4MX0.wchiJxghFpKAUXLFTDHbb0r1ZKF5eozUtyLCe44pzgI"
for i in $(seq 1 15); do curl -sS -o /dev/null -w "%{http_code}\n" -X POST "http://localhost:8000/ask" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"question\":\"t $i\"}"; done
401
401
401
401
401
401
401
401
401
401
401
401
401
401
401
```

**Đúng port 8002 — rate limit student (10 req/phút): 15 request → 10×200 rồi 5×429**

```text
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0NDAwODEsImV4cCI6MTc3NjQ0MzY4MX0.wchiJxghFpKAUXLFTDHbb0r1ZKF5eozUtyLCe44pzgI"
for i in $(seq 1 15); do
  curl -sS -o /dev/null -w "%{http_code}\n" \
    -X POST "http://localhost:8002/ask" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"question\":\"t $i\"}"
done
200
200
200
200
200
200
200
200
200
200
429
429
429
429
429
```

### Exercise 4.4: Cost guard implementation

Cách làm trong code `04-api-gateway/production/cost_guard.py`:

- **Trước khi gọi LLM:** `cost_guard.check_budget(username)` — so sánh chi phí đã dùng trong ngày với ngân sách **per-user** (`daily_budget_usd`, mặc định $1/ngày) và tổng **global** (`global_daily_budget_usd`, mặc định $10/ngày). Vượt budget user → trả **402**; vượt budget global → trả **503**.
- **Sau khi có câu trả lời:** `record_usage` cộng token (ước lượng từ số từ trong `question` và `answer`) và quy đổi sang USD theo hệ số giá input/output trên 1K token; cập nhật tổng cost global.
- **Đọc trạng thái:** `GET /me/usage` (có JWT) trả `cost_usd`, `budget_remaining_usd`, v.v.; phần `usage` trong response `/ask` (vd. `budget_remaining_usd`) phản ánh cost sau lượt gọi đó.

Trong phiên test trên, `/ask` thành công trả `usage` với `budget_remaining_usd` còn dư; chưa spam đủ để bắt buộc thấy **402/503** trong log nộp bài.

---

## Part 5: Scaling & Reliability


**5.1 — Stateless + Redis session**

- `POST /chat`: body `question` + `session_id` (tuỳ chọn). Không gửi `session_id` thì server tạo UUID mới.
- State không nằm trong RAM của process: mỗi session là JSON trong Redis key `session:<session_id>` (`setex` TTL mặc định 3600s trong `save_session`). Nếu Redis không kết nối được lúc khởi động → fallback **in-memory** (cảnh báo trong log, không scale được).
- History tối đa **20 message** (cắt tail trong `append_to_history`). Có thêm `GET /chat/{session_id}/history`, `DELETE /chat/{session_id}`.
- Response có `served_by` = biến môi trường `INSTANCE_ID` hoặc `instance-<hex>` — để thấy request do replica nào xử lý; dữ liệu hội thoại vẫn đọc/ghi chung qua Redis.

**5.2 — Health vs readiness**

- `GET /health`: `status` = `ok` hoặc `degraded` (khi bật Redis mà `ping` lỗi), kèm `instance_id`, `uptime_seconds`, `storage`, `redis_connected`.
- `GET /ready`: chỉ khi **đang dùng Redis** thì bắt buộc `ping` OK mới **200**; lỗi Redis → **503** (phù hợp làm readiness cho orchestrator).

**5.3 — Shutdown**

- `lifespan` log khi start (`Starting instance …`) và khi app tắt (`Instance … shutting down`). File này **không** cài thêm cơ chế drain hàng đợi hay từ chối request đang xử lý; phần “reliability” chủ yếu là **state nằm ngoài process** + health/ready.

**5.4 — Compose + Nginx**

- Stack: **redis** (Alpine, `healthcheck`, `maxmemory` + `allkeys-lru`), **agent** (nhiều replica), **nginx** publish `8080:80`, agent không expose port ra host (chỉ qua mạng nội bộ).
- `nginx.conf`: upstream `agent:8000` (DNS Compose round-robin tới các task `agent`), `proxy_next_upstream` khi lỗi/timeout/503, thêm header **`X-Served-By`** (`$upstream_addr`) — khác với trường JSON `served_by` trong body (đó là `INSTANCE_ID` của app).
- Scale nhiều agent: theo hướng dẫn trong compose/README dùng `docker compose up --scale agent=3` (và/hoặc cấu hình `deploy.replicas` tùy môi trường Compose).

**5.5 — `test_stateless.py` (kịch bản có sẵn)**

- Gọi `http://localhost:8080` (qua Nginx), **5 lần** `POST /chat` cùng một `session_id` sau lượt đầu.
- In ra `served_by` mỗi lượt; nếu **>1** instance trong set → minh chứng load balancing. Cuối script `GET /chat/{session_id}/history` để xác nhận toàn bộ lượt vẫn nối được **một** chuỗi hội thoại dù instance khác nhau (nhờ Redis).
- Nếu chỉ thấy **1** instance: script nhắc tăng scale (`--scale agent=3`).
