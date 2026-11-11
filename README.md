# Daily cartoon shorts

Every day a GitHub Action writes a 30-second tall-tale cartoon story with the free Gemini API, voices it in several languages (edge-tts, free), renders a 1080x1920 video with Remotion, and uploads each language to YouTube. No server, no paid service.

## One-time setup

1. **Gemini key (free):** create a key at https://aistudio.google.com/apikey and add it as the repo secret `GEMINI_API_KEY`.
2. **YouTube upload (free):**
   - In Google Cloud Console create a project, enable **YouTube Data API v3**, and create an **OAuth client ID** of type *Desktop app*. Download the JSON as `client_secret.json`.
   - OAuth consent screen: set the publishing status to **In production**. In *Testing* mode Google expires the refresh token after 7 days and uploads stop.
   - Run once on any machine (Termux works): `pip install google-auth-oauthlib` then `python scripts/get_refresh_token.py client_secret.json`. Open the printed URL on the same device, approve, and copy the three values it prints.
   - Add them as repo secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
3. **Test:** Actions tab, *Daily cartoon shorts*, *Run workflow*. With *upload* off it only renders; the MP4s appear as the `videos` artifact. Turn *upload* on when you like the result.

The schedule (`cron` in `.github/workflows/daily.yml`) runs daily at 08:00 IST. Scheduled runs always upload.

## Customise

- `config.json`: languages and voices (edge-tts voice names), privacy, Gemini model.
- `scripts/pipeline.py`: the story prompt and the topic categories.
- `src/Story.tsx`: the look of the cartoon.

## Limits to know

- YouTube API default quota allows about 6 uploads per day per Google Cloud project (an upload costs 1,600 of 10,000 units). Four languages a day fits. More needs a quota extension request.
- Uploads from an unaudited API project can be forced to private by YouTube. If that happens, request an API compliance audit, or set the videos public by hand.
- Public repos get free Actions minutes with no cap. Private repos get 2,000 a month.
- Topic history is saved in `data/history.json` so topics don't repeat.
- Videos use synthetic voices. Keep the "Made with AI-assisted tools" line in the description, and check YouTube's current disclosure and repetitive-content rules.
