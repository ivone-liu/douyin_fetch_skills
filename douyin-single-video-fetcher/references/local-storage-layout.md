# Local Storage Layout

Recommended local layout for the single-video pipeline:

```text
storage/
  raw_api/
    douyin_single_video/
      2026-03-22/
        <aweme_id>.json
  normalized/
    douyin_single_video/
      <aweme_id>.json
  downloads/
    videos/
      <creator-slug>/
        <aweme_id>.mp4
    music/
      <creator-slug>/
        <music-key>.mp3
  analysis_md/
    <creator-slug>/
      <aweme_id>.md
```

Rules:
- raw JSON is immutable evidence
- normalized JSON is the compact machine record
- markdown is the downstream analysis source
- database stores only the searchable, high-value index fields
