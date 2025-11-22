# Frontend Metadata Upgrade Guide

_Last updated: November 22, 2025_

## Summary
- `features.translation_languages` now returns an ordered list of objects with `language_code` and `language_name` instead of bare strings.
- Both `providers.translation.supported_languages` and `providers.tts.supported_languages` follow the same object shape, so every metadata consumer sees a consistent schema.
- No other metadata sections changed, but clients that previously assumed strings must normalize their parsing logic before deploying.

## API Response Example
```json
{
  "providers": {
    "translation": {
      "provider": "google",
      "supported_languages": [
        { "language_code": "en", "language_name": "English" },
        { "language_code": "fi", "language_name": "Suomi" },
        { "language_code": "zh-CN", "language_name": "简体中文" },
        { "language_code": "zh-TW", "language_name": "繁體中文" }
      ]
    },
    "tts": {
      "provider": "google",
      "supported_languages": [
        { "language_code": "fi", "language_name": "Suomi" }
      ]
    }
  },
  "features": {
    "translation_languages": [
      { "language_code": "en", "language_name": "English" },
      { "language_code": "fi", "language_name": "Suomi" },
      { "language_code": "zh-CN", "language_name": "简体中文" },
      { "language_code": "zh-TW", "language_name": "繁體中文" }
    ],
    "tts_languages": ["fi"],
    "tts_submission_workers": 4
  }
}
```
## Required Frontend Changes
1. **Update typing/models**: Change any `string[]` typings for `translation_languages` *and* both `providers.*.supported_languages` collections to `Array<{ language_code: string; language_name: string }>`.
2. **Parsing logic**: When reading `/metadata`, remove calls that upper-case raw strings; instead, rely on `language_code` for logic and `language_name` for UI labels.
3. **Feature toggles**: If UI uses the supported translation list to gate locale dropdowns, surface the localized `language_name` directly. Fallback to `language_code` when the name is missing.
4. **TTS badges**: Because only Finnish (`fi`) is supported for TTS generation, ensure dropdowns and copy reflect the single available locale.

## Testing Checklist
- [ ] Snapshot tests or schema validations updated to expect the structured objects.
- [ ] Manual verification of the locale picker rendering each `language_name` correctly.
- [ ] QA for flows that previously assumed English-only labels (bulk import, metadata footer, etc.).
- [ ] Confirm that any analytics events emitting translation languages send the `language_code` string, not the entire object.

## Rollout Notes
- Ship the frontend change before or alongside the backend deployment to avoid runtime errors.
- No environment flags are available for fallback; clients should deploy as soon as the new backend hits staging.
