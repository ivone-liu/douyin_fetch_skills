# Local Storage Layout

The single-video pipeline does not require a free-form external storage root.
It writes into the skill pack itself so the storage contract stays fixed across environments.

Default layout:

```text
openclaw-douyin-skills/
  data/
    creators/
      <creator-slug>/
        raw_api/
          douyin_single_video/
            <yyyy-mm-dd>/
              <aweme_id>.json
        normalized/
          douyin_single_video/
            <aweme_id>.json
        downloads/
          videos/
            <aweme_id>.<ext>
          music/
            <music-key>.<ext>
        analysis_md/
          <aweme_id>.md
```

Rules:
- each creator has one dedicated subtree under `~/.openclaw/workspace/data/creators/`
- raw JSON is immutable evidence
- normalized JSON is the compact machine record
- markdown is the preferred downstream analysis source
- database stores only searchable, high-value index fields
- scripts derive this root from their own location, so path conventions stay stable after install
