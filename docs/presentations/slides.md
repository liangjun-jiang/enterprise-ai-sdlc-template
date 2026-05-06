# Slides source — edit here, then regenerate slides.html

Presenter: Liangjun Jiang
Date: April 8, 2026

---

## Slide 1 — Title

**Title:** Cloud-based AI-SDLC with Existing CI/CD

**Subtitle:** Moving AI from individual laptops into shared, automated pipelines

---

## Slide 2 — Today's Developer Experience

Each developer has their own AI setup:
- Uses Cursor's chat feature for prompts
- Connects to Confluence, Jira, CI/CD (CircleCI, JFrog, Jenkins, Spinnaker, ArgoCD etc) via Skills or MCP
- AI value is real but limited to coding tasks
- Gets the job done with the tremendous token cost

**The problem:**
- Every request rebuilds the same context from scratch
- Same project docs sent to the LLM by every developer, every time
- Token cost = N developers × M requests — most of it redundant
- No shared knowledge, no lifecycle automation, no team-level visibility

---

## Slide 3 — The Approach: GitHub-Centric AI + Human SDLC

> Be real — humans always need to be in the loop.

4 Pillars:
1. **Claude SDK** — Code is generated in the cloud. Context built once, persisted, and shared across the team and the LLM.
2. **GitHub Actions** — Automates the SDLC workflows from Issue to code generation, review, lint, test, CI/CD, and context update.
3. **GitHub Issues** — Requirements and human review start here. No new tools. Product owners, PMs, and Developers work in the same place.
4. **Git Branches + PRs** — Each step has a human gate. Merging a PR triggers the next automated stage.

---

## Slide 4 — Pipeline Flow (Mermaid diagram)

Mental model: Issue → human review/refine/approve → AI code gen on feature branch → human code review → CI tests → human merge approval → dev

```mermaid
flowchart LR
    A([Issue<br/>feature / bug / task]) --> B
    B([Human Review<br/>Refine & Approve]) -->|approved| C
    C([AI Code Gen<br/>feature branch]) --> D
    D([Code Review<br/>PR]) -->|approved| E
    E([CI<br/>lint / test]) -->|pass| F
    F([Merge Approval]) -->|merge| G
    G([dev branch<br/>+ Context Update])

    style A fill:#eff6ff,stroke:#2563eb,color:#0f172a
    style B fill:#fffbeb,stroke:#b45309,color:#0f172a
    style C fill:#f0fdf4,stroke:#16a34a,color:#0f172a
    style D fill:#fffbeb,stroke:#b45309,color:#0f172a
    style E fill:#f0fdf4,stroke:#16a34a,color:#0f172a
    style F fill:#fffbeb,stroke:#b45309,color:#0f172a
    style G fill:#eff6ff,stroke:#2563eb,color:#0f172a
```    
Caption: Amber = Human gate (PR approval) · Green = AI-automated step

---

## Slide 5 — Demo

Demo video recorded separately.

**What the demo shows:**
- GitHub Issue created with a feature request
- Developer reviews and approves the Issue
- AI generates code on a feature branch via GitHub Actions (Claude SDK)
- PR opened automatically; reviewer approves
- CI runs lint + tests; merge to dev
- Issue Closed with Branch link

---

## Slide 6 — Challenges

1. **LiteLLM gateway not accessible from Procore IT's AWS account**
   - Used a personal GitHub account and a demo project for this demo
