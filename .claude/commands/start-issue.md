# Start Issue

Set up an issue branch and display the issue for review. Lightweight — no planning or implementation.

## Arguments

- `$ARGUMENTS` — the GitHub issue number (e.g., `16`)

## Workflow

1. **Verify we're on a milestone branch**:

   ```bash
   git branch --show-current
   ```

   Must match `milestone/*`. If not, check if there is exactly one local `milestone/*` branch and switch to it. If zero or multiple, stop and ask the user to run `/start-milestone` first.

2. **Ensure clean working tree**:

   ```bash
   git status --porcelain
   ```

   If uncommitted changes exist, stop and ask the user to commit or stash.

3. **Fetch the issue details**:

   ```bash
   gh issue view $ARGUMENTS --json number,title,body,milestone,labels
   ```

4. **Derive a short slug** from the issue title (lowercase, 4-5 meaningful words, hyphens).

5. **Create the issue branch**:

   ```bash
   git checkout -b issue/$ARGUMENTS-<slug>
   git push -u origin issue/$ARGUMENTS-<slug>
   ```

6. **Update the GitHub issue**:

   ```bash
   gh issue edit $ARGUMENTS --add-label "in progress" --add-assignee @me
   ```

   Create the "in progress" label first if it doesn't exist (use `#0075CA` blue).

7. **Output**:
   - The issue branch name
   - The issue title and body
   - The milestone branch it will merge back into
   - "Review the issue, then run `/implement` to plan and build it."
