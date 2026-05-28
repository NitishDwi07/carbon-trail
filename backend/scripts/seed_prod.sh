#!/bin/bash
# Run this ONCE after first deploy via Render Shell or Railway console:
#   bash scripts/seed_prod.sh
set -e
cd "$(dirname "$0")/.."
echo "Running migrations..."
python manage.py migrate
echo "Seeding demo data..."
python manage.py seed_demo
echo "Done. Login: analyst / password123"
