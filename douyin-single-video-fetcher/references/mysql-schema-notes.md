# MySQL Schema Notes

The SQL file lives at `db/douyin_media_schema.sql`.

Design choices:
- Do not store full raw API payloads in MySQL.
- Store raw payloads as local files and keep their paths in the database.
- Keep one row per video in `videos`.
- Keep one row per music asset in `music_assets`.
- Connect them through `video_music_map`.
- Track fetch events in `api_fetch_logs`.
- Treat local markdown analysis files as the preferred downstream source.
