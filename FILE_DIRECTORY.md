# Backdoor Network File Directory

## Root

- `.env.example`
- `README.md`
- `package.json`
- `index.html`
- `vite.config.ts`
- `tailwind.config.ts`
- `backend/`
- `src/`

## Backend

```text
backend/
  main.py
  requirements.txt
  __init__.py
  api/
    routes.py
  models/
    contact.py
    internship.py
  services/
    cv_matching.py
    email_enrichment.py
    internsg_scraper.py
    linkedin_search.py
    message_generator.py
    outreach_tracker.py
    scoring_engine.py
    strategy_engine.py
  storage/
    database.py
```

## Frontend (Core App Flow)

```text
src/
  App.tsx
  main.tsx
  pages/
    Dashboard.tsx
    Internships.tsx
    Contacts.tsx
    Outreach.tsx
    Home.tsx
    NotFound.tsx
  services/
    pipelineApi.ts
    api.ts
  lib/
    pipelineState.ts
    utils.ts
  hooks/
    useCV.ts
```

## UI Components

```text
src/components/
  ContactCard.tsx
  CVUploadPrompt.tsx
  JobInput.tsx
  LinkedInFallbackCard.tsx
  MessageDrawer.tsx
  SentCard.tsx
  TopNav.tsx
  ui/
    (shadcn/ui component set)
```
