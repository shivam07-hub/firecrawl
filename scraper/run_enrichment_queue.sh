#!/bin/bash
# Sequential enrichment queue — runs all priority companies in order.
# LM Studio must be running (gemma-3-4b / fast model).
# Usage: bash run_enrichment_queue.sh [--workers N]
set -e
cd "$(dirname "$0")"

WORKERS=${1:-4}
LOG=../logs/enrich_queue_$(date +%Y%m%d_%H%M%S).log

run() {
    local company="$1"
    echo "=== $(date '+%H:%M:%S') Starting: $company ===" | tee -a "$LOG"
    python3 supabase_enricher.py --company "$company" --workers "$WORKERS" 2>&1 | tee -a "$LOG"
    echo "" | tee -a "$LOG"
}

# Priority order: volume × impact
run "Barclays"
run "State Street"
run "DBS Bank"
run "Novartis"
run "Adobe"
run "DXC Technology"
run "Paytm"
run "NXP Semiconductors"
run "Target"
run "Autodesk"
run "Maersk"
run "3M"
run "Intel"
run "Meesho"
run "Razorpay"
run "PhonePe"
run "Haleon"
run "Airbnb"
run "Morgan Stanley"
run "WESCO"
run "Storable"
run "CRED"
run "Solvay"
run "BlackBerry"
run "Freshworks"
run "Dell"
run "Michelin"
run "Mastercard"
run "Philips"
run "Airbus"
run "Engie"
run "American Express"
run "Synopsys"
run "Thoughtworks"
run "Visa"
run "Chanel"
run "Eli Lilly"
run "Schneider Electric"
run "Salesforce"
run "Zomato"

# Partial-enrich companies (have some skills, backfill the rest)
run "Accenture"
run "Cognizant"
run "Wells Fargo"
run "Sanofi"
run "Fidelity Investments"
run "Stripe"
run "LDC (Louis Dreyfus)"

echo "=== $(date '+%H:%M:%S') Queue complete ===" | tee -a "$LOG"
echo "Log: $LOG"
