# Collaboration Collaboration Rules

When working on a project that uses Collaboration, follow these rules.

## Before editing files

1. Call `collaboration.declare_intent` with exact files and purpose
2. If `conflict` is returned, stop editing immediately and call `collaboration.wait_for_clear`
3. After `cleared`, run `git pull --rebase` then re-declare intent

## After editing files

1. Run relevant tests
2. Call `collaboration.report_done` with a summary of changes

## If you need to edit additional files

1. Call `collaboration.extend_lock` with additional files and reason
2. If `partial_conflict`, only edit non-conflicting files

## Never

- Edit files without declaring intent first
- Continue editing after receiving a conflict
- Accept zip files as source of truth; use Git
- Skip report_done
- Push when there are unresolved conflicts

## API quick reference (local service, default http://localhost:8080)

- Declare: `POST /api/collaboration/intent/declare`
- Wait:    `POST /api/collaboration/intent/wait_for_clear`
- Done:    `POST /api/collaboration/intent/done`
- Extend:  `POST /api/collaboration/intent/extend`
- Status:  `GET  /api/collaboration/status/{room_id}`
