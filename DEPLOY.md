# Deploying on a VPS with Coolify

The app runs from [docker-compose.yml](docker-compose.yml). **The only thing you set in Coolify is `OPENAI_API_KEY`.**

## About the database

The app doesn't need a database server. Its storage is:
- **JSON files**: both memories, the chats, and app state
- **an SQLite file**: the embedding cache

All of it lives in the Docker volume `esd-data`, defined in the Compose file. Docker creates the volume on the first start; you don't set anything up. It survives redeploys and restarts.

On the first start, the container copies in a ready-made demo snapshot, so **Load demo history** is instant.

## Steps

> **Pushing to GitHub does not deploy anything by itself.** Coolify only builds a repository after you add it as a resource (steps 1–5). After that, you either press **Deploy** yourself or set up auto-deploy (step 7).

The repository is `https://github.com/naeemsadik/ESD-Lite` (public), branch **`main`**. `.env` and `data/` are git-ignored, so your key and your local chats are not in it.

1. **Open a project.** In Coolify, go to **Projects**, open a project (or create one), and pick an environment such as **production**.
2. **Add the repository.** Click **+ New** → **Public Repository**. Paste `https://github.com/naeemsadik/ESD-Lite` and click **Check repository**.
3. **Build settings:**
   - **Branch:** `main`
   - **Build Pack:** change it from Nixpacks to **Docker Compose**
   - **Base Directory:** `/`
   - **Docker Compose Location:** `/docker-compose.yml`

   Then click **Continue**.
4. **Environment Variables tab:** add `OPENAI_API_KEY` with your key as the value. That is the only variable. If it's missing, the deploy stops with an error rather than starting a broken app.
5. **Domain.** Coolify generates a URL automatically, from `SERVICE_FQDN_ESD_8501` in the Compose file; it appears on the service in the **General** tab. To use your own domain instead, set it to `https://esd.yourdomain.com:8501`. The `:8501` tells Coolify which container port to use; visitors still use normal HTTPS.
6. **Click Deploy** (top right). Watch the **Deployments** tab: the first build takes a few minutes, mostly installing Python packages. When the status turns **Running (healthy)**, open the URL. In the sidebar, click **Reset everything**, then **Load demo history**, and follow [docs/demo_script.md](docs/demo_script.md).
7. **Optional: auto-deploy on every push.**
   1. In the resource, open the **Webhooks** tab. Copy the **GitHub** webhook URL and set a webhook secret.
   2. On GitHub, go to repository **Settings → Webhooks → Add webhook**. Paste the URL, set content type to `application/json`, use the same secret, and choose the "push" event.
   3. Alternatively, connect Coolify's **GitHub App** and add the repository through it (**+ New → Private Repository (with GitHub App)**). That enables auto-deploy automatically.

**Updating:** push to GitHub, then press **Redeploy** in Coolify (or let the webhook do it). The `esd-data` volume, and with it your memories and chats, is kept.

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
