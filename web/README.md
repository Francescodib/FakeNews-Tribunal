# FakeNews Tribunal — Web UI

Next.js 16 frontend for the FakeNews Tribunal fact-checking platform.

## Stack

- **Next.js 16** — App Router
- **React 19**
- **Tailwind CSS 4** — CSS-based configuration (no `tailwind.config.ts`)
- **TypeScript**

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Requires the API running at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

## Environment

```bash
# .env.local (optional — defaults to http://localhost:8000)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Pages

| Route | Description |
|---|---|
| `/` | Redirect to `/dashboard` or `/login` |
| `/login` | Login form |
| `/register` | Registration form |
| `/dashboard` | Stat overview, claim submission, paginated history |
| `/analysis/[id]` | Live SSE stream + verdict display + PDF export |
| `/batch` | Batch submissions with live polling |
| `/profile` | Change email / password |
| `/admin/users` | User management (admin only) |

## Production build (Docker)

Built via `web/Dockerfile` with Next.js standalone output. See root `docker-compose.yml`.

```bash
docker compose up web -d
```
