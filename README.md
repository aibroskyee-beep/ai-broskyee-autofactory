# AI-Broskyee AutoFactory v1

A free-only starter pipeline for: trend feed scan → original short script/storyboard → procedural Blender 3D render → speech + generated music bed → MP4 technical QA → optional automatic publishing.

## Hard rules
- No paid model fallback. AI text generation calls only OpenRouter's `openrouter/free` router when `OPENROUTER_API_KEY` is configured. If unavailable, the run stops or uses the explicitly labelled offline fallback; it never switches to a paid model.
- Nothing in this package adds billing, enables a paid service, or publishes unless credentials are configured.
- The renderer creates a new, original stylized 3D video. It does not copy the Zack D. Films video, script, characters, audio, or shots. Its visual quality is a prototype; it is not yet equivalent to the reference.
- QA currently verifies decodeability, dimensions, duration, stream presence, black/frozen frames and audio levels. Automated QA cannot guarantee that every visual is semantically perfect; inspect early outputs.
- Private GitHub Actions usage is blocked in the current project. Standard GitHub-hosted Actions are free for public repositories, but a public repository exposes its source code. This package contains no tokens. Do not make the existing private repo public merely to run this package; use a separate public repo containing only these files if you choose that route.
- YouTube/Instagram publishing requires official account authorization. Instagram's publishing API needs the video at a public HTTPS URL. The workflow uses a temporary GitHub Release asset for this purpose only when run in a public repo. YouTube API client projects may be limited to private uploads until the required YouTube audit is passed.

## Local smoke test
1. Install Blender and FFmpeg only if you choose to run locally. Your laptop is not the intended full-render machine.
2. Set `OPENROUTER_API_KEY` in your local environment only if you already have a free-tier key. Do not paste keys into ChatGPT or commit them.
3. Use `python app/scout.py --out work/trends.json` to test public feed discovery.
4. Use `python app/story_writer.py --trends work/trends.json --out work/plan.json` to generate an original plan.
5. Render using Blender: `blender --background --python app/render_story.py -- work/plan.json work/visual.mp4`.
6. Generate narration/music with Piper installed and a compatible English voice model; see the workflow.

## Free cloud route
The included GitHub Actions workflow is meant for a separate public repository if you decide code visibility is acceptable. It runs once per day at 19:00 India time and can also be launched manually. This is not installed into or pushed to your private project by this package. Free quotas, services and provider eligibility can change; the workflow fails closed rather than switching to paid services.

## Publishing setup is a required one-time step
- Add `OPENROUTER_API_KEY` only if the account has access to free models; no payment method is needed or should be added for this project.
- Add YouTube OAuth client/refresh-token secrets only after authorizing your own channel through the official Google flow.
- Add Instagram Login API user ID and access token after authorizing your own Creator account through Meta's official developer flow.
- Give the GitHub Actions token `contents: write` only in the separate publishing repo so it can create and delete a temporary release asset. Never include personal access tokens in source files.
- If any platform blocks publishing, the run reports the failure; it does not bypass restrictions or use browser automation.

## v1 limitations
- One original video is built per run; it is not a claim of guaranteed virality or income.
- Trend feeds indicate current interest but do not prove facts. Scripts are designed as original entertainment/explainers and avoid unsupported precise claims.
- Best posting time starts with 19:00 IST and must later be adjusted from actual platform analytics. It is not claimed to be personalized until analytics are connected.
- Repeated generic AI templates can be ineligible for monetization. Keep each episode materially original, fact-check stories and add distinctive creative value.
