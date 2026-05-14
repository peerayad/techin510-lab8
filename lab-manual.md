# Week 8 Lab Manual: Evaluations
## Table of Contents

- [Week 8 Lab Manual: Evaluations](#week-8-lab-manual-evaluations)
  - [Table of Contents](#table-of-contents)
  - [Learning Objectives](#learning-objectives)
  - [Component A: Interview](#component-a-interview)
    - [Staff Interview](#staff-interview)
    - [During the Interview](#during-the-interview)
    - [Synthesis Artifact: JTBD Statement](#synthesis-artifact-jtbd-statement)
  - [Component B: Lab](#component-b-lab)
  - [Component C: System Architecture \& Design](#component-c-system-architecture--design)
    - [C.1 User Flow Diagram](#c1-user-flow-diagram)
    - [C.2 Risk Labels](#c2-risk-labels)
    - [C.3 Design Decision Log](#c3-design-decision-log)
  - [Component D: Tests \& Evaluations](#component-d-tests--evaluations)
    - [D.1 Evaluation Design](#d1-evaluation-design)
    - [D.2 Golden Test Set](#d2-golden-test-set)
    - [D.3 Run Your Evaluation](#d3-run-your-evaluation)
    - [D.4 Report Your Results](#d4-report-your-results)
  - [Submission](#submission)
    - [Deliverables](#deliverables)
  - [Reflection](#reflection)

---

## Learning Objectives

After completing this lab, you will be able to 

1. design and perform systematic evaluations of your agentic systems
2. present/visualize evaluation results
3. perform data-driven decision-making on your system design

---

## Component A: Interview

### Staff Interview

**Kevin** manages the makerspace and purchasing of consumables such as hardware components. 

**Current pain:** Processing paperwork around purchasing is time consuming.

### During the Interview

- Write down **exact phrases** the interviewee uses (their language, not your paraphrase)
- Listen for frustrations, workarounds, and gaps (these are design opportunities)

### Synthesis Artifact: JTBD Statement

After the interview, write a Jobs-to-be-Done statement:

> **"When [interviewee] is [situation], they want to [motivation] so they can [outcome]."**
---

## Component B: Lab

Build a web app for Kevin based on your JTBD.

Additional constraints for your build:

1. Include an agent in the web app so that Kevin can ask questions about purchasing data.
2. The agent should be guardrailed to mitigate hallucination and keep responses to Kevin safe.

---

## Component C: System Architecture & Design

In Component C, document how Kevin moves through your app and where the agentic system can fail. Your evaluation in Component D should test the specific risk points you identify here.

### C.1 User Flow Diagram

Sketch the user flow diagram. You may use a hand sketch, Mermaid, Excalidraw, Figma, screenshots with arrows, or another visual format.

Your flow should start with Kevin's goal and end with the app's response or action. Include the major screens, decisions, and system steps.

### C.2 Risk Labels

On your user flow diagram, label the places where the system could fail. Use short labels such as `HALLUCINATION`, `ERROR`, `INFO LEAK`, and `UNSAFE RESPONSE`.
These risk labels are the starting point for your golden test set in Component D.

### C.3 Design Decision Log

Create a short design decision log with **3-5 decisions** that affect your user flow and evaluation. Each decision should connect the system design to what you will test.

At least one decision must answer this question:

> **Which data structure is suitable for this project: SQL, NoSQL/document data, CSV/spreadsheet, or another format? Justify your choice based on Kevin's workflow.**

Good decisions to document include:

- Which data structure you chose for purchasing records and why
- Which data source the agent is allowed to use
- Which errors should produce a user-facing message vs. a developer log
- What information should be logged for later evaluation

---

## Component D: Tests & Evaluations

In Component D, you will design and run your own tests and evaluations. The goal is to show what you tested, what passed, what failed, what improved, and what still needs caution.

You need to present quantitative results for:

1. the effectiveness of your build 
2. the safety of your agent

### D.1 Evaluation Design

For each evaluation above, define:

- **Metric:** what number you will report
- **Scoring rule:** how you decide the score
- **Threshold:** what result counts as acceptable
- **Evaluator:** who computes the metric and how

### D.2 Golden Test Set

Create a golden test set of at least **12 test cases**. A golden test set is a fixed set of seed inputs you can rerun whenever the system changes.


Note that your golden set should include happy-path cases, edge cases to serve your evaluation purposes.

### D.3 Run Your Evaluation

Run each test in golden set through your app and record the result. You may run the evaluation manually or write a small script.

### D.4 Report Your Results

Create a short evaluation report. The report should contain the raw evaluation results and key takeaways drawn from the data. If there is any failure identified in your test, analyze the failure.
Please choose appropriate visualizations for your results.
Analyzing your resuls, and suggest one improvement of your system (implementation is not needed).


---

## Submission

Submit all artifacts to Github classroom and merge to main branch. Ensure all results are reproducible. 

### Deliverables

Your submission should include:

1. A working web app for Kevin's purchasing workflow
2. A staff interview synthesis artifact with your JTBD statement
3. A user flow diagram with labeled system risks
4. A design decision log with 3-5 decisions
5. An evaluation design for build effectiveness and agent safety
6. A golden test set with at least 12 test cases
7. Raw evaluation results and a short evaluation report with visualizations
8. A brief reflection answering the prompts below


---

## Reflection

Answer briefly:

1. Which evaluation result surprised you most?
2. Which failure would create the most real-world risk for Kevin?
3. What would you test next if this app were going to be used for a month?

---
