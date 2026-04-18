# Finish Issue

Squash-merge a PR, close the issue, delete the branch, and return to the milestone branch.

## Arguments

- `$ARGUMENTS` — the GitHub issue number (e.g., `16`). If omitted, infer from the current branch name (`issue/<number>-*`).

## Workflow

1. **Determine the issue number and PR**:

   If no argument, extract from current branch name. Find the open PR:

   ```bash
   gh pr list --head "$(git branch --show-current)" --state open --json number,title,url,baseRefName
   ```

   If no PR exists, stop and tell the user to run `/commit-push-pr` first.

2. **Identify the target branch** from the PR's `baseRefName` (should be `milestone/*`). If it targets `main`, warn the user.

3. **Pre-merge check**:

   ```bash
   pre-commit run --all-files
   ```

   If any checks fail, report and stop.

4. **Squash-merge the PR**:

   ```bash
   gh pr merge <pr-number> --squash --delete-branch
   ```

5. **Close the GitHub issue**:

   ```bash
   gh issue close $ARGUMENTS --comment "Resolved via PR #<pr-number>."
   ```

6. **Return to the milestone branch**:

   ```bash
   git checkout <milestone-branch>
   git pull origin <milestone-branch>
   ```

   Clean up the local issue branch if it still exists:

   ```bash
   git branch -d issue/$ARGUMENTS-* 2>/dev/null
   ```

7. **List remaining milestone issues**:

   ```bash
   gh issue list --milestone "<milestone title>" --state open --json number,title
   ```

8. **Report**:
   - Issue closed, PR merged, branch deleted, now on milestone branch
   - Remaining open issues
   - If issues remain: "Run `/start-issue <number>` for the next issue"
   - If none remain: "All issues complete. Run `/finish-milestone <version>` to create the milestone PR"

## Important

- Never force-merge if pre-commit checks are failing.
- Issue PRs must target the milestone branch, not `main`.
