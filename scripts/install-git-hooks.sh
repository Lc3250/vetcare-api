#!/usr/bin/env bash
# Підключає каталог scripts/git-hooks як джерело git-хуків для цього клону.
git config core.hooksPath scripts/git-hooks
echo "git hooks підключено: scripts/git-hooks"
