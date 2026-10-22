# V0.4 deployment: Render + external persistence

Render free web services have an ephemeral filesystem. Never use SQLite, an upload folder, or `/tmp` as a durable library on Render. A paid Render disk is a separate option but is **not** the backend implemented here. This app requires PostgreSQL and S3-compatible storage for library mode.

Official references: [Render free service limitations](https://render.com/docs/free), [Render disks](https://render.com/docs/disks), [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html).

## 1. External database

Provision a durable PostgreSQL database (managed PostgreSQL, Supabase PostgreSQL, Neon, or paid Render PostgreSQL). Check retention/expiry and backups; Render's free database is not a permanent production retention plan. Use a dedicated database/app role. Set `DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB?sslmode=require` with URL-encoded credentials. The application uses psycopg and creates additive v1 metadata tables on startup. The role needs CREATE for first startup; future schema changes need explicit migrations. Enable TLS and database backups. No document binaries are stored in SQL.

## 2. Private object store

Create a dedicated private S3 bucket (AWS S3 or a compatible provider such as R2). Disable public/anonymous access, public ACLs and public bucket policies; enable encryption at rest using the provider's bucket defaults. Do not configure a public bucket URL. The server proxies authenticated downloads; no signed or public URLs are exposed.

Create a restricted access key. AWS policy example (replace BUCKET):

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":"arn:aws:s3:::BUCKET/books/*"}]}
```

No list-bucket permission is required by the app. Do not enable object-lock retention that prevents deletion without documenting its effects. If versioning is enabled, set an explicit noncurrent-version lifecycle: API deletion creates a delete marker, not immediate physical erasure. Logical quota excludes historic versions. Test denial of unauthenticated access, including guessed object paths, before uploading private data. The app relies on operator bucket policy; it cannot infer every compatible provider's public-access configuration.

Set `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. For AWS omit `S3_ENDPOINT_URL`; for R2 set its HTTPS S3 API endpoint and region `auto`. Do not use a public website endpoint. TLS verification remains enabled. Object keys contain stable account IDs and random book IDs; filenames are metadata only.

## 3. Accounts

Use `python -m app.security` locally for each distinct 32+ random-character password. It prompts without echo and outputs a salted scrypt hash. Set `LIBRARY_USERS` to a JSON object mapping stable account names to hashes. Names allow letters, digits, underscore and hyphen, up to 64 characters. Never reuse a username for another person; never set one shared demo password for all users.

Deliver credentials separately via your existing secure channel. There is no account-email flow. Use HTTPS only. Close a private browser window to clear its cached Basic login. Rotating/removing an account's hash revokes the old password after restart. Removing an account does not erase its books: delete them before removal or temporarily reprovision that same identity for cleanup.

`DEMO_ACCESS_TOKEN` is legacy temporary-demo authentication; it cannot enable private libraries and is insufficient in hosted production mode.

## 4. Render Blueprint

Connect the GitHub repository to Render and use `render.yaml`. It creates a Docker web service on the free plan, one worker, running as an unprivileged user. Supply all unsynced secrets/settings in Render. Set `APP_ENV=production`; Render's own flag also enforces this. Missing accounts, missing external persistence, or SQLite causes startup failure. Set the health check to `/health`; it reports process liveness, **not** external provider health. Storage operations report failures to users without leaking provider errors.

The app writes only bounded, disposable upload/parser temporary files locally and deletes parser directories after success/failure/timeout. Hard instance termination may interrupt a request; temporary files disappear with the instance, and reserved external entries remain visible for cleanup. Nothing relies on the local disk surviving a restart.

The service does not automatically deploy or create/bill external services. External storage and database must be configured by the operator. Free tiers may sleep, expire or impose quotas: confirm current provider terms. The 100 MiB ceiling does not guarantee that every textbook fits Render's RAM/request deadline. A timed-out browser request is not proof the upload failed; refresh the book list before retrying.

## 5. Acceptance checks before inviting users

1. Sign in as Alice and save each supported type. Reopen the browser and select saved books without re-uploading.
2. Sign in as Bob; Alice's list is absent and her IDs return 404 for text, original, annotation and deletion.
3. Restart/redeploy Render. The same originals and book list must remain accessible.
4. Exhaust byte/count quotas. Concurrent requests must not oversubscribe. Delete a book and verify capacity returns.
5. Revoke object-storage access during a write/delete. The UI must report failure, retain quota/pending metadata and allow cleanup after restoring access.
6. Verify anonymous object reads fail, no credentials appear in frontend source, and HTTPS is enforced by Render.
7. Back up SQL and objects, test restore together, and configure object-version lifecycle and provider budget alerts.

## Scaling beyond this MVP

Keep provisioned users trusted. Before a public multi-tenant launch, add separate parser containers with no network/credentials, malware scanning, persistent asynchronous jobs, upload resumability, distributed authentication/abuse controls and account lifecycle/audit tooling. This MVP intentionally fails bounded processing attempts rather than accepting unbounded background work.
