#!/bin/bash
pylint --rcfile .github/linters/.python-lint bot.py
markdownlint -c .github/linters/.markdown-lint.yml README.md

