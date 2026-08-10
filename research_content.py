"""Authoritative participant-facing copy for the research instrument.

The wording in this module was transcribed from the supplied research workbook.
Keeping it separate from page rendering makes future text-only revisions safe and
easy to review without changing validation, persistence, or questionnaire behaviour.
"""

from __future__ import annotations

from typing import Final

DOCTORAL_RESEARCH_TITLE: Final[str] = (
    "Cultural Determinants of Environmental Responsiveness: Consumer Culture’s "
    "Influence on Airlines’ Strategies for Sustainable Aviation."
)
INSTITUTION_LINE: Final[str] = (
    "Doctoral Research | University of the Aegean | Department of Tourism "
    "Economics and Management"
)
RESEARCHER_NAME: Final[str] = "Anargyros Ziakas"
RESEARCHER_ROLE: Final[str] = "PhD Candidate, University of the Aegean"
SUPERVISOR_NAME: Final[str] = "Professor Andreas Papatheodorou"
CONTACT_EMAIL: Final[str] = "anargyrosziakas@aegean.gr"

INVITATION_PARAGRAPHS: Final[tuple[str, ...]] = (
    (
        "Dear Expert/Scholar,"
    ),
    (
        "You are kindly invited to participate in an expert evaluation forming "
        "part of the doctoral research entitled:"
    ),
    (
        "The research is conducted by Anargyros Ziakas, PhD Candidate at the "
        "Department of Tourism Economics and Management, University of the "
        "Aegean, under the supervision of Professor Andreas Papatheodorou."
    ),
    (
        "This questionnaire applies the Fuzzy DEMATEL method to examine the "
        "causal relationships among cultural, economic and strategic factors "
        "associated with sustainable airline strategy. Based on your professional "
        "knowledge and experience, you will evaluate direct relationships within "
        "three groups of criteria and then among the three dimensions themselves. "
        "There are no right or wrong answers."
    ),
    (
        "Participation is entirely voluntary, and you may leave the questionnaire "
        "at any time before submitting your responses, without providing a reason "
        "or experiencing any negative consequences."
    ),
    (
        "The questionnaire is designed to collect responses anonymously. You will "
        "not be asked to provide your name, email address, employer or other "
        "directly identifying information. Your responses will remain confidential "
        "and will be used exclusively for academic research purposes. The data will "
        "be stored securely and accessed only by the researcher and, where "
        "academically necessary, the supervisory team."
    ),
)

METHOD_PURPOSE_PARAGRAPHS: Final[tuple[str, ...]] = (
    (
        "The Decision-Making Trial and Evaluation Laboratory method, commonly "
        "referred to as DEMATEL, is used to examine and structure causal "
        "relationships among a set of interrelated factors. Rather than assessing "
        "the factors independently, the method evaluates the extent to which each "
        "factor directly influences the others."
    ),
    (
        "The resulting analysis helps to identify the factors that exert the "
        "greatest influence on the overall system; determine which factors are most "
        "strongly affected by other factors; distinguish between cause and effect "
        "factors; and develop a structured causal model illustrating the "
        "relationships among the criteria."
    ),
    (
        "The present questionnaire applies the Fuzzy DEMATEL approach. Fuzzy logic "
        "is used because expert judgements may involve uncertainty and cannot "
        "always be expressed precisely through a single numerical value."
    ),
)

EVALUATION_INSTRUCTIONS: Final[tuple[str, ...]] = (
    (
        "For each pair of factors, please assess: To what extent does the "
        "influencing factor directly affect the other factor?"
    ),
    (
        "Please evaluate only the direct influence of one factor on another, based "
        "on your professional knowledge, experience and judgement."
    ),
    (
        "The direction of influence is important. For example, the influence of C1 "
        "on C4 may be different from the influence of C4 on C1. Therefore, each "
        "direction must be evaluated separately."
    ),
    (
        "The online questionnaire presents four matrices in sequence. The row is "
        "always the cause and the column is always the affected factor. "
        "Self-influence relationships are disabled and are not answers."
    ),
    (
        "There are no right or wrong answers. Please select the response that most "
        "accurately reflects your professional judgement."
    ),
)

DIRECT_INFLUENCE_REMINDER: Final[str] = (
    "Please focus on the strength of the direct influence, rather than whether the "
    "two factors are generally related or correlated."
)
CONSENT_STATEMENT: Final[str] = (
    "I confirm that I have read and understood the information above and "
    "voluntarily agree to participate in this research."
)
THANK_YOU_MESSAGE: Final[str] = (
    "Your professional judgement is highly valuable to this doctoral research and "
    "will contribute to the identification of the most influential and most "
    "affected factors within the proposed sustainable airline strategy framework."
)
ANONYMITY_REMINDER: Final[str] = (
    "To preserve anonymity, please do not add your name, employer or other directly "
    "identifying information."
)
