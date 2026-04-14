from __future__ import annotations

from backend.models.contact import Contact
from backend.models.internship import Internship


class MessageGenerator:
    def generate(
        self,
        contact: Contact,
        internship: Internship,
        cv_excerpt: str,
        university: str,
    ) -> dict[str, str]:
        cv_line = cv_excerpt[:220].replace("\n", " ")
        shared_context = f"I noticed your path in {contact.role}"
        if university and university.lower() in contact.education.lower():
            shared_context = f"We both share a {university} background"

        email = (
            f"Subject: Interest in {internship.role} at {internship.company}\n\n"
            f"Hi {contact.name},\n\n"
            f"I am applying for the {internship.role} internship at {internship.company}. "
            f"{shared_context}, so I wanted to reach out for advice on standing out for this role.\n\n"
            f"My CV highlights: {cv_line}\n\n"
            "If you are open to it, I would value a short call or any guidance on how to align better with the team.\n\n"
            "Thank you for your time."
        )

        linkedin = (
            f"Hi {contact.name}, I am exploring the {internship.role} internship at {internship.company}. "
            f"{shared_context} and would appreciate any quick advice on what the team values most."
        )

        return {"email": email, "linkedin": linkedin}
