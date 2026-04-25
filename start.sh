#!/bin/zsh
source .venv/bin/activate
set -a
source .env
set +a
neurocore --help
