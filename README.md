# Daily News Briefing

A scheduled Python job that reads configured RSS/Atom feeds, matches recent items to keyword topics, optionally summarises them with an LLM, and sends each topic to ntfy. It exits after each run; it does not run as a service.

## Setup

Requires Python 3.11+. Install locally with:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Edit `config/topics.yaml` to set feeds, topic names, keywords, optional excludes/feed restrictions, timezone, and model names. Feed and topic changes require only this YAML file. The sample config uses BBC RSS feeds; replace them with your trusted sources as needed. Keyword matching is case-insensitive substring matching against title and feed summary.

For local credentials, copy `.env.example` to `.env` (a private `.env` is already created for this checkout) and fill in `OPENAI_API_KEY`, `NTFY_TOPIC`, and `LLM_PROVIDER`. The app loads `.env` automatically, and `.env` is ignored by Git. Create an OpenAI API key in the OpenAI developer platform; API billing is separate from a ChatGPT subscription. This project is preconfigured to use `gpt-6-luna`, a cost-efficient model; change `settings.models.openai` in YAML to select another model. Without an LLM key, use `--no-llm` to send matched headlines.

Set `NTFY_TOPIC` for delivery. `NTFY_SERVER` is optional and defaults to `https://ntfy.sh`; `NTFY_TOKEN` is optional for a protected topic. In the ntfy app, subscribe to the same topic. On the public ntfy.sh server, anyone who knows or guesses the topic name can read and publish to it. Use a long random topic name (24+ random characters), an access token on a protected topic, or self-host ntfy. Store `NTFY_TOPIC`, `NTFY_TOKEN`, provider keys, and `LLM_PROVIDER` as GitHub Actions secrets, never in the repository or YAML. Notification text may appear on a lock screen; do not include private information.

## Run

```sh
python -m briefing.main --dry-run --no-llm
python -m briefing.main --dry-run
python -m briefing.main
python -m briefing.main --hours 12
```

Dry-run prints notifications and does not send or update seen state. The `--no-llm` mode is useful to check feed fetching and keyword matches. Normal runs write delivered item IDs to `state/seen.json`, preventing repeated stories. Feed failures are reported in a low-priority Briefing notes notification and do not stop other feeds.

## Schedule

GitHub Actions runs daily at 07:00 UTC and can also be started with workflow dispatch. Edit the cron expression in `.github/workflows/briefing.yml` to change it; GitHub schedule times are UTC and may run with some delay. The configured timezone controls time-window interpretation and notification date display.

## Future work

- Fetch and summarise full article text, including paywall handling with `trafilatura`.
- Add email or Telegram delivery.
- Change topics through a chat message.
- Use LLM-based topic classification instead of keyword matching.
