Viewed rooms.py:1-257

If you wanted to take **Think Twice** from running on a single instance to a fully horizontally scalable, enterprise-grade architecture (like running it across 10 Kubernetes pods or EC2 instances), here is the exact list of every bottleneck currently in your codebase and how to fix them:

### 1. In-Memory WebSocket State (The Biggest Bottleneck)

- **The Problem:** In `backend/routers/websockets.py`, your `ConnectionManager` stores all active websocket connections in a local Python dictionary (`self.game_connections = {}`). If Player A connects to Server 1 and Player B connects to Server 2, Server 1 has no idea Player B exists. Calling `broadcast_game()` on Server 1 will only update Player A.
- **The Solution:** Introduce a **Pub/Sub Broker (like Redis)**. When a game event happens, instead of broadcasting directly from the dictionary, the server publishes the event to a Redis channel (e.g., `game_123_updates`). Every server subscribes to this channel and forwards the payload to any local websockets it manages.

### 2. Database Connection Churn (`NullPool`)

- **The Problem:** In `database.py`, you are using `poolclass=NullPool`. This was a smart choice for a single serverless container because it prevents idle connections. But if you scale to 10 instances handling thousands of requests, every single API call will open and close a new TCP connection to PostgreSQL. PostgreSQL will immediately crash under the connection overhead (it usually maxes out at a few hundred connections).
- **The Solution:** Deploy a connection pooler like **PgBouncer** in front of your database. You would switch SQLAlchemy back to a standard `QueuePool`, connect to PgBouncer, and let PgBouncer multiplex thousands of virtual connections into just 50 actual database connections.

### 3. Synchronous Database Calls in an Async Framework

- **The Problem:** If you look at `rooms.py`, your endpoints are defined as standard functions (`def create_room(...)`), not async (`async def`), and you are using the synchronous SQLAlchemy engine. FastAPI handles this by pushing these requests into a background thread pool. If you get a massive spike in traffic, you will exhaust the thread pool, and the server will lock up.
- **The Solution:** Upgrade to **SQLAlchemy Async** (`ext.asyncio.create_async_engine` and `AsyncSession`). Change your routes to `async def` and use `await db.execute(...)`. This allows a single worker to handle massive I/O bound database queries concurrently without thread locking.

### 4. Background Tasks Blocking the Event Loop

- **The Problem:** You are heavily using `BackgroundTasks` in `rooms.py` to trigger your WebSocket broadcasts (`background_tasks.add_task(manager.broadcast_game...)`). These tasks execute on the same event loop after the HTTP response is sent. Under heavy load, thousands of queued background tasks will start eating CPU cycles, slowing down the server's ability to accept _new_ incoming HTTP requests.
- **The Solution:** Offload background processing to a dedicated task queue like **Celery**, **arq** (for async Python), or publish events directly to **Kafka/Redis** and have a separate microservice just for handling WebSocket broadcasts.

---

**Summary for an Interview:**
_"To scale horizontally, I would need to extract state from the individual application servers. I'd move WebSocket state-sharing to **Redis Pub/Sub**, add **PgBouncer** to prevent connection starvation, and migrate my SQLAlchemy implementation to fully **Async I/O**."_
