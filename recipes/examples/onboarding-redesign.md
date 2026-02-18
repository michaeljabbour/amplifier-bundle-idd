# Onboarding Redesign

## Intent
Make the onboarding flow significantly faster for new users.

### Success Criteria
- New users complete setup in under 2 minutes
- Flow works on both web and mobile
- No new dependencies added to the project

### Scope
- In scope: onboarding screens, auth flow, profile setup
- Out of scope: post-onboarding experience, billing

## Trigger
On demand. Human initiates explicitly.

### Pre-Conditions
- Access to both web and mobile codebases

### Confirmation
- Present decomposition plan before executing
- Wait for human approval

## Agents & Sequence
1. Explorer and Researcher work in parallel
   - Explorer: understand current onboarding implementation
   - Researcher: find onboarding best practices
2. Zen Architect synthesizes findings into a proposed design
3. Builder implements the design
4. Zen Architect reviews implementation against success criteria

## Context
- context/project (auto-detected)
- Explorer output feeds into Architect input
- Researcher output feeds into Architect input
- Architect output feeds into Builder input

## Behaviors
- behaviors/review-before-ship
- behaviors/log-all-decisions
