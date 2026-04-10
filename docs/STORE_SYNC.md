# Syncing to the community store

When you change this packaging repo, copy the updated app files into
[harmalh/umbrel-community-store](https://github.com/harmalh/umbrel-community-store)
under `harmalh-executive-ai-assistant/`.

Files to sync:

- `executive-ai-assistant/docker-compose.yml`
- `executive-ai-assistant/umbrel-app.yml`
- `executive-ai-assistant/assets/icon.svg`

When syncing to the community store, adjust:

1. `id` in `umbrel-app.yml` to `harmalh-executive-ai-assistant`
2. icon URL to the raw file inside `harmalh/umbrel-community-store`
3. `APP_HOST` in `docker-compose.yml` to `harmalh-executive-ai-assistant_ui_1`

Checklist: `harmalh/umbrel-community-store/docs/RELEASE_CHECKLIST.md`
