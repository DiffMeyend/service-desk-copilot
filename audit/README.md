# Audit

This directory contains audit artifacts and schemas that are intentionally kept separate from the GPT runtime uploads to save tokens and prevent unintended retrieval.

## Contents
- `logs/` -- local audit logs only
- `schema/` -- audit telemetry schema used by tooling

## Upload Policy
- Do not upload audit logs or audit schemas to the GPT knowledge set.
- Share audit files with the GPT only when explicitly needed for a specific task.
