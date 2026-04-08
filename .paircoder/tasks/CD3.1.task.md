---
id: CD3.1
title: 'Add operator_id column to user profile   | Repo: bpsai-support (Function App)'
plan: plan-sprint-3-engage
type: feature
priority: P0
complexity: 5
status: done
sprint: '3'
depends_on: []
---

# Add operator_id column to user profile   | Repo: bpsai-support (Function App)

Add `operator_id` column to the user model in the Function App. Auto-generate on user creation as `{first_name_lower}-{random_8_chars}`. Must be unique.

# Acceptance Criteria

- [x] `operator_id` column added to user model (String, unique, nullable=True initially)
- [x] Auto-generation logic: `first_name.lower() + "-" + secrets.token_hex(4)` (8 hex chars)
- [x] Migration adds column
- [x] If user has no first name, fall back to `user-{random_8_chars}`
- [x] Unique constraint prevents collisions (regenerate on conflict)
- [x] GET user endpoint returns `operator_id`
- [x] Tests: generation format, uniqueness, fallback
