# Welcome to your Lovable project

TODO: Document your project here

## Environment setup

- Keep secrets in `.env` at the project root only.
- If `.env` is missing, run `npm run setup:env` to recreate it from `.env.example`.
- Set `TINYFISH_API_KEY` in `.env` before using InternSG discovery.

## Strict data quality mode

The backend internship pipeline runs in strict TinyFish-first mode:

- Internships are sourced from TinyFish scraping InternSG only.
- Query expansion is rule-based (`Machine Learning` -> `ml intern`, `ai intern`, etc.).
- Internship rows are accepted only when required fields are present:
  - `company`, `role/title`, `description`, `requirements`
- Duplicate internships are removed by `(company, role)`.
- No synthetic internship fallbacks are returned.
- If TinyFish cannot return valid internships, the API returns an error.

### Contact and email quality rules

- Contacts must have valid person-style LinkedIn profile URLs (`linkedin.com/in/...`).
- No placeholder contacts are generated.
- Emails are accepted only when sourced from real extracted data:
  - InternSG application email (`HIGH`)
  - provider lookup stub result (`MEDIUM`)
- Guessed emails (`careers@...`, `firstname@...`) are not generated.

### Run quality checklist

- Expanded queries are logged.
- TinyFish row count is logged.
- Merged internship row count and final returned count are logged.
- Pipeline should fail explicitly when no valid internships are found.
