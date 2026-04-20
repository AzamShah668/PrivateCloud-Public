# How to Merge azams-branch to main

This guide explains how to safely merge the development branch (`azams-branch`) to `main` while **excluding the sprint journal and internal documentation** (`.claude/` directory).

---

## Why Exclude `.claude/` from main?

The `.claude/` directory contains:
- **Sprint journal entries** — Development tracking, not production code
- **Internal documentation** — Planning, architecture notes for Claude Code
- **Temporary plans** — Not meant for the final codebase

These are useful for development but should **NOT** be merged to the production `main` branch.

---

## Step-by-Step: Safe Merge to main

### Step 1: Make sure you're on main

```bash
git checkout main
git pull origin main
```

### Step 2: Start the merge (but don't complete it yet)

```bash
git merge --no-commit --no-ff azams-branch
```

Explanation:
- `--no-commit` = Stage the merge but don't commit (gives you time to review)
- `--no-ff` = Create a merge commit (good practice for tracking branch history)

### Step 3: Remove the .claude/ directory from the merge

```bash
git rm -r .claude
```

This **removes** `.claude/` from what will be merged, but it's safe:
- The directory still exists in `azams-branch`
- It won't be in `main`
- Both branches are independent

### Step 4: Verify what will be merged

```bash
git status
```

You should see:
- Files from your feature branches (the actual code changes)
- `.claude/` directory listed as "deleted" (which is what you want)
- NO other unexpected files

### Step 5: Complete the merge

```bash
git commit -m "Merge branch 'azams-branch' into main

Features:
- Admin portal (backend APIs + React frontend)
- Enhanced VM management
- Improved UI/UX with animations
- Admin user creation documentation

Sprint documentation and internal notes remain in azams-branch only.
Production-ready code is merged to main."
```

### Step 6: Push to main

```bash
git push origin main
```

---

## Result

After this merge:

| Directory | main | azams-branch |
|-----------|------|--------------|
| `/backend`, `/frontend`, etc. | ✅ Production code | ✅ Development code |
| `/ADMIN_SETUP.md` | ✅ Public docs | ✅ Public docs |
| `/.claude/journal/` | ❌ NOT in main | ✅ In branch for reference |
| `/.claude/docs/` | ❌ NOT in main | ✅ In branch for reference |

---

## Verify the Merge Worked

After pushing to main, verify on GitHub:

```bash
# Check main branch contents
git checkout main
ls -la

# You should NOT see .claude/ here
# But you SHOULD see all your feature code
```

Visit GitHub: https://github.com/verventech/PrivateCloud/tree/main

- You'll see the actual feature code (backend, frontend, admin portal)
- You WON'T see the `.claude/` directory
- The branch (`azams-branch`) still has it for reference

---

## If You Make a Mistake

If you complete the merge without removing `.claude/`:

```bash
# Undo the last commit (before pushing)
git reset --soft HEAD~1

# Now remove .claude/ and recommit
git rm -r .claude
git commit -m "Merge branch 'azams-branch' into main (without internal docs)"
```

Or if you already pushed:

```bash
# Remove from main after merging
git rm -r .claude
git commit -m "Remove internal documentation from main"
git push origin main
```

---

## What Happens to azams-branch?

The branch stays unchanged:
- All sprint journals are still there
- You can reference them anytime
- You can create a new feature branch from here for Sprint 4

```bash
# Start Sprint 4 from this branch
git checkout azams-branch
git checkout -b sprint-4-features
```

---

## Automating This in Future

If you do this merge regularly, you can automate the removal:

```bash
# Create a file at .gitattributes
echo ".claude/ merge=ours" >> .gitattributes
git add .gitattributes
git commit -m "Configure git to exclude .claude/ from merges"
```

Then future merges will automatically exclude `.claude/` without manual removal.

---

## Questions?

- Need to recover `.claude/` on main? Just check out azams-branch: `git show azams-branch:.claude`
- Want to keep sprint docs on main? Skip the `git rm -r .claude` step (but not recommended for production)
- Need to revert the merge? `git reset --hard HEAD~1` (before pushing)
