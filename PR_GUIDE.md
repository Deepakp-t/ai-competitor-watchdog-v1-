# Pull Request Guide

## Quick Steps to Create a PR

### 1. Create a Feature Branch
```powershell
# Make sure you're on main and it's up to date
git checkout main
git pull origin main

# Create a new branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Edit your code/design files
- Test your changes

### 3. Commit Your Changes
```powershell
git add .
git commit -m "Add: Description of your changes

- What changed
- Why it changed
- Any breaking changes"
```

### 4. Push to GitHub
```powershell
git push origin feature/your-feature-name
```

### 5. Create Pull Request on GitHub

1. Go to: https://github.com/Deepakp-t/ai-competitor-watchdog-v1-/pulls
2. Click **"New Pull Request"**
3. Select:
   - **Base branch**: `main`
   - **Compare branch**: `feature/your-feature-name`
4. Fill in PR details:
   - **Title**: Brief, descriptive title
   - **Description**: 
     ```markdown
     ## Changes
     - What you changed
     - Why you changed it
     
     ## Review Focus
     - [ ] Code quality
     - [ ] Design/architecture
     - [ ] Performance
     - [ ] Testing
     
     ## Testing
     - How you tested this
     
     ## Screenshots/Examples (if applicable)
     ```
5. **Request Reviewers**: Add your teammate's GitHub username
6. Click **"Create Pull Request"**

## PR Best Practices

### Good PR Title Examples
- `feat: Add Twitter monitoring via search API`
- `fix: Resolve SQLAlchemy detached instance error`
- `refactor: Improve change detection logic`
- `docs: Update setup instructions`

### Good PR Description Template
```markdown
## Summary
Brief description of what this PR does.

## Changes
- Change 1
- Change 2
- Change 3

## Why
Explanation of why this change is needed.

## Testing
- [ ] Tested locally
- [ ] Unit tests pass
- [ ] Integration tests pass

## Screenshots/Demo
(If applicable)

## Related Issues
Closes #123
```

## Requesting Specific Review Types

### Code Review
- Focus on: Logic, error handling, performance, best practices
- Mention: "Please review for code quality and logic"

### Design Review
- Focus on: Architecture, patterns, scalability, maintainability
- Mention: "Please review for design and architecture decisions"

### Both
- Mention: "Please review for both code quality and design"

## After Creating PR

1. **Notify your teammate** (Slack, email, etc.)
2. **Address review comments** by pushing more commits to the same branch
3. **Mark conversations as resolved** when you've addressed feedback
4. **Request re-review** when ready

## Updating Your PR

If you need to make changes after creating the PR:

```powershell
# Make your changes
git add .
git commit -m "Address review feedback: description"
git push origin feature/your-feature-name
```

The PR will automatically update with your new commits!
