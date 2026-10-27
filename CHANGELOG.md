## Unreleased

## 2.4.3 - 2026-10-27

### Added
- Windows .NET/WPF installer using the self-contained widget build.
- Persistent Windows placement, startup and always-on-top behavior.
- Official Claude and Codex usage collectors with reset details in popovers.

### Fixed
- Windows installer no longer targets protected `Program Files` directories.

## 2.4.2 - 2026-10-26

### Added
- Native .NET/WPF Windows widget installer.
- Real Windows collectors for Claude Code, Cursor, Codex and FreeLLMAPI.
- FreeLLMAPI configuration and detailed usage panel.

### Fixed
- Windows installer now installs per-user without requiring access to `Program Files`.
- Codex session reading works while the active rollout is locked by Codex.
