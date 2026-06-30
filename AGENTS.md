# Pair Mesh Collaboration Rules

When working on a project that uses Pair Mesh, follow these rules.

## Before editing files

1. Call `pair_mesh.declare_intent` with exact files and purpose
2. If `conflict` is returned, stop editing immediately and call `pair_mesh.wait_for_clear`
3. After `cleared`, run `git pull --rebase` then re-declare intent

## After editing files

1. Run relevant tests
2. Call `pair_mesh.report_done` with a summary of changes

## If you need to edit additional files

1. Call `pair_mesh.extend_lock` with additional files and reason
2. If `partial_conflict`, only edit non-conflicting files

## Never

- Edit files without declaring intent first
- Continue editing after receiving a conflict
- Accept zip files as source of truth; use Git
- Skip report_done
- Push when there are unresolved conflicts

## API quick reference (local service, default http://localhost:8080)

- Declare: `POST /api/pair-mesh/intent/declare`
- Wait:    `POST /api/pair-mesh/intent/wait_for_clear`
- Done:    `POST /api/pair-mesh/intent/done`
- Extend:  `POST /api/pair-mesh/intent/extend`
- Status:  `GET  /api/pair-mesh/status/{room_id}`
