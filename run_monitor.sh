#!/bin/bash
# Science Podcast Monitor - Automated Daily Run
# Runs via cron, generates digest, and pushes to GitHub

cd /root/science-podcast-monitor

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

source venv/bin/activate

echo "$(date): Starting podcast monitor..."

# Pull latest changes first
echo "$(date): Pulling latest from GitHub..."
git pull --rebase origin main || {
    echo "$(date): Pull failed, resetting to origin/main"
    git fetch origin
    git reset --hard origin/main
}

# Run the monitor (max 5 episodes to control costs)
python main.py --email --max 5

# Commit and push results
if [[ -n $(git status --porcelain) ]]; then
    echo "$(date): Changes detected, committing..."
    git add -A
    git commit -m "Automated podcast digest $(date +%Y-%m-%d)"
    git push origin main
    echo "$(date): Pushed to GitHub"
else
    echo "$(date): No changes to commit"
fi

echo "$(date): Done"
