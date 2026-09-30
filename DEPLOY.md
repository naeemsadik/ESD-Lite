# Deploying on a VPS with Coolify

The app runs from [docker-compose.yml](docker-compose.yml). **The only thing you set in Coolify is `OPENAI_API_KEY`.**

## About the database

The app doesn't need a database server. Its storage is:
- **JSON files**: both memories, the chats, and app state
- **an SQLite file**: the embedding cache

All of it lives in the Docker volume `esd-data`, defined in the Compose file. Docker creates the volume on the first start; you don't set anything up. It survives redeploys and restarts.

On the first start, the container copies in a ready-made demo snapshot, so **Load demo history** is instant.

## Steps

1. **Push the project to GitHub.** A private repository is fine. `.env` and `data/` are git-ignored, so your key and your local chats are never uploaded.
2. **In Coolify:** create a new **Resource**, pick your repository, and choose the **Docker Compose** build pack. The Compose file location is `/docker-compose.yml`.
3. **Environment Variables:** add **`OPENAI_API_KEY`** = your key. That is the only variable. If it's missing, the deploy stops with an error rather than starting a broken app.
4. **Domain:** Coolify generates a URL automatically, from `SERVICE_FQDN_ESD_8501` in the Compose file. To use your own domain, set the service's domain to `https://esd.yourdomain.com:8501`. The `:8501` tells Coolify which container port to use; visitors still use normal HTTPS on port 443.
5. **Deploy.** The first build takes a few minutes, mostly installing Python packages. The container reports healthy once `/_stcore/health` answers.
6. **Open the URL.** In the sidebar, click **Reset everything**, then **Load demo history**, and follow [docs/demo_script.md](docs/demo_script.md).

**Updating:** push to GitHub, then press **Redeploy** in Coolify. The `esd-data` volume, and with it your memories and chats, is kept.

## Before you share the URL

- **There is no login.** Anyone with the URL can chat, and every message is paid for with your OpenAI key. Set a **monthly spending limit** in the OpenAI dashboard, and only share the link with the people who need it.
- **It's a single-user demo.** Everyone who opens the URL shares the same memory and chats.

## If something goes wrong

| Symptom | Cause / fix |
|---|---|
| Deploy fails with a message about `OPENAI_API_KEY` | The variable isn't set in Coolify, or is misspelt. |
| Red error above the chat: "AuthenticationError" or "RateLimitError" | The key is wrong, or the OpenAI account has no credit or has hit its limit. |
| The graphs are blank | The viewer's browser can't reach the graph library's CDN (cdnjs / jsdelivr). Check their internet or firewall. |
| The first "Load demo history" after changing the memory code takes 1–2 minutes | Expected. The snapshot is rebuilt once when the memory code changes, then saved in the volume. |
| The container is "unhealthy" | Check the logs in Coolify. The app listens on port 8501 inside the container. |
