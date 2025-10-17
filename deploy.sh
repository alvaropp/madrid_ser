#!/bin/bash
# Deploy script: Generate map and push to gh-pages

set -e  # Exit on error

echo "🚀 Deploying to GitHub Pages..."
echo ""

# Generate the map
echo "📊 Generating map..."
python generate_map.py

echo ""
echo "📤 Deploying to gh-pages branch..."

# Save the current branch
CURRENT_BRANCH=$(git branch --show-current)

# Stash any uncommitted changes on main
git stash

# Switch to gh-pages branch
git checkout gh-pages

# Copy the generated index.html from main
git checkout main -- index.html

# Commit the update
git add index.html
git commit -m "Update map - $(date '+%Y-%m-%d %H:%M')" || echo "No changes to commit"

# Push to remote
git push origin gh-pages

# Switch back to original branch
git checkout "$CURRENT_BRANCH"

# Restore any stashed changes
git stash pop 2>/dev/null || true

echo ""
echo "✅ Deployment complete!"
echo "🌐 Your map will be live at: https://alvaropp.github.io/madrid_ser/"
echo "   (may take a few minutes to update)"
