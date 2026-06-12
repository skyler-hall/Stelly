# Stelly — Multi-Machine Sync

Quick reference for keeping the same Stelly checkout in sync across the Mac, Raspberry Pi, and Windows PC.

Repo: https://github.com/skyler-hall/Stelly

---

## Daily workflow (any machine)

```bash
cd ~/Projects/Stelly      # or wherever you cloned it on this machine
git pull                  # grab anything pushed from another machine
# ...do work...
git add -A
git commit -m "what changed"
git push
```

If `git pull` reports merge conflicts, fix the conflicting files, then `git add` them and `git commit` to finish the merge before pushing.

---

## One-time setup per machine

### Mac (already done)

`gh` 2.93+ installed via Homebrew, authenticated as `skyler-hall` with HTTPS + git credential helper. Pushes/pulls don't prompt.

### Raspberry Pi (Raspberry Pi OS / Debian / Ubuntu)

```bash
# 1. Install git and GitHub CLI
sudo apt update
sudo apt install -y git
(type -p wget >/dev/null || sudo apt install -y wget) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
  && sudo apt update \
  && sudo apt install -y gh

# 2. Sign in (HTTPS, login with web browser, authenticate Git: Yes)
gh auth login

# 3. Clone
mkdir -p ~/Projects && cd ~/Projects
gh repo clone skyler-hall/Stelly
cd Stelly
```

### Windows PC

Install via [winget](https://learn.microsoft.com/windows/package-manager/) (built into Windows 10/11) — open PowerShell:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
# Restart PowerShell so PATH picks up `git` and `gh`

gh auth login          # GitHub.com, HTTPS, login with web browser, Yes to auth Git
mkdir $HOME\Projects -ErrorAction SilentlyContinue
cd $HOME\Projects
gh repo clone skyler-hall/Stelly
cd Stelly
```

---

## Useful one-liners

```bash
git pull --rebase           # cleaner history when syncing in
git status                  # what's changed locally
git log --oneline -10       # recent commits
gh repo view --web          # open the repo on github.com
```

## If a push is rejected

Usually means another machine pushed first. Pull, then push again:

```bash
git pull --rebase
git push
```
