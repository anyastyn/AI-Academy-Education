# Role Workflow: AI-DS (AI Data Scientist)
# Author: Anna Styn
# Date: 2026-02-10

## Step 1: Define quality metrics
- Input: scope from AI-PM + governance rules
- Action: define what “good” means (groundedness, correctness, usefulness, safety, latency)
- Output: metrics + target thresholds
- Depends on: AI-PM

## Step 2: Collect baseline results
- Input: current agent version + sample flows/questions
- Action: run 10–20 test cases, record outputs
- Output: baseline scorecard
- Depends on: AI-SE/FDE provides stable test script

## Step 3: Create evaluation test set
- Input: typical Power Automate scenarios
- Action: create a “golden set”:
  - flows (small/medium/large)
  - missing-info cases
  - security edge cases (secret pasted)
- Output: versioned test set + expected outcomes

## Step 4: Run experiments
- Input: old vs new agent versions
- Action: compare:
  - memory on/off
  - doc RAG on/off
  - Planning+ReAct prompt vs old prompt
- Output: experiment table

## Step 5: Analyze failures
- Input: experiment outputs
- Action: categorize failures (retrieval wrong, hallucination, missing questions, unsafe handling)
- Output: top failure modes + improvements

## Step 6: Report
- Input: analysis
- Action: write evaluation report + recommendations
- Output: report for AI-PM/AI-SE

## Step 7: Iterate
- Input: approved improvements
- Action: update prompt/retrieval/tests and re-run
- Output: improved scores and updated report
