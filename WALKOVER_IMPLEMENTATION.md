# Khel Club – Walkover Match Outcome

## Overview

This project extends the Khel Club tournament management system to support Walkover as a match outcome.

A Walkover occurs when one participant cannot compete and the opposing participant is declared the winner without playing the match. The implementation supports Walkover declaration, result persistence, winner progression and frontend visualization while preserving regular match scoring.

## 1. Existing Scoring Mechanism

The existing system uses Flask, SQLAlchemy and MySQL for match and score management.

- Matches are associated with tournaments and participating teams.
- Scores are maintained through the scoring endpoints.
- The score update endpoint processes match scores and determines the winner when a match is finalized.
- Completed matches can progress their winners to successor matches in knockout tournaments.
- The frontend retrieves match and score information to display fixtures and results.

## 2. Changes Implemented

### Backend

- Introduced `result_type` to distinguish regular matches from other match outcomes.
- Added `is_walkover` to identify Walkover matches.
- Implemented `POST /declare-walkover`.
- Added validation for match, tournament, participants and finalized match state.
- Persisted the winning team, completed status and Walkover outcome.
- Prevented finalized matches from being modified through override requests.
- Updated match response data to expose Walkover metadata.
- Updated knockout progression logic to advance Walkover winners to successor matches.
- Ensured future knockout participants use SQL NULL instead of invalid placeholder team IDs.

### Frontend

- Added Walkover declaration and result visualization.
- Added a visible Walkover indicator.
- Highlighted the winning participant.
- Suppressed numerical scores for Walkover results.
- Added Walkover presentation to match fixtures and knockout brackets.
- Ensured pending matches do not display placeholder scores as actual results.
- Selected the knockout view by default for elimination tournaments.

## 3. Database Schema Changes

Added the following fields to the Match model:

| Field | Purpose |
|---|---|
| `result_type` | Identifies the match outcome type |
| `is_walkover` | Indicates whether the match ended through Walkover |

The `result_type` field defaults to `regular`.

Existing foreign-key constraints are preserved. Unassigned future-round participants are represented using SQL NULL rather than dummy team IDs.

Apply the corresponding database migration before running the application.

## 4. Assumptions

- A Walkover can only be declared for a valid match with participating teams.
- A valid winning team must be one of the match participants.
- A finalized match cannot be modified.
- Walkover results do not require numerical scores.
- A Walkover winner advances through the existing knockout progression mechanism.
- Regular matches continue using the existing scoring workflow.

## 5. Future Improvements

- Introduce additional result types such as forfeits and byes.
- Centralize outcome validation and progression rules further as new outcomes are added.
- Introduce role-based authorization for declaring match outcomes.
- Improve audit logging for match result changes.
- Expand integration and end-to-end test coverage.
- Improve frontend accessibility and result history.

## Testing

### Backend

Command:

```bash
./venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Result: 23 tests passed.

### Frontend

Command:

```bash
npm run build
```

Result: Production build successful; 37 static pages generated.

### Manual Verification

- Walkover declaration through the API.
- Database persistence of Walkover results.
- Protection against modifying finalized matches.
- Four-team knockout bracket creation.
- Automatic progression of both semifinal Walkover winners into the final.
- Walkover indicators in both knockout visualization modes.
- Pending final displayed without fake numerical scores.

## Technology Stack

- Backend: Python, Flask, SQLAlchemy
- Database: MySQL
- Frontend: Next.js, React
- Testing: Python unittest, Next.js production build
