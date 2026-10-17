#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="xansar1/fraudshield-ai"
REMOTE="https://github.com/${REPO}.git"
cd "$ROOT"
if ! command -v git >/dev/null 2>&1; then echo "Git is required"; exit 1; fi
if ! git ls-remote "$REMOTE" >/dev/null 2>&1; then
  echo "First create EMPTY public GitHub repository at: https://github.com/new"
  echo "Repository name: fraudshield-ai | Owner: xansar1"
  echo "Do not initialize with README or .gitignore (both already included)."
  exit 2
fi
if [ ! -d .git ]; then
  git init -b main
fi
EXISTING="$(git remote get-url origin 2>/dev/null || true)"
if [ -n "$EXISTING" ]; then
  case "$EXISTING" in
    "$REMOTE"|"git@github.com:${REPO}.git") ;;
    *) echo "Refusing to change unexpected origin: $EXISTING"; exit 3;;
  esac
else
  git remote add origin "$REMOTE"
fi
git add .gitignore .vercelignore .python-version README.md PORTFOLIO_CARD.md Dockerfile \
  render.yaml vercel.json requirements.txt requirements-dev.txt \
  app.py app/ ml/ models/ data/synthetic_transactions.csv scripts/ \
  tests/ run.command .github/
if ! git diff --cached --quiet; then
  git commit -m "Ship FraudShield AI V2: explainable synthetic fraud-risk demo"
fi
git branch -M main
git push -u origin main
echo "Published: https://github.com/${REPO}"
