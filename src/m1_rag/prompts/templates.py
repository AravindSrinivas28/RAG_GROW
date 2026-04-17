"""Static refusal copy and generation instructions (rag-architecture.md §6–7)."""

# Educational links for refusal / abstention (not investment advice).
EDUCATIONAL_URL_AMFI = "https://www.amfiindia.in/investor-education/investor-education.html"
EDUCATIONAL_URL_SEBI = "https://investor.sebi.gov.in/"

REFUSAL_ADVISORY_TEXT = (
    "I can’t provide investment advice, fund comparisons, or recommendations. "
    "I only share factual information from official sources when available. "
    "For general investing concepts, see the AMFI investor education page linked below."
)

REFUSAL_PII_TEXT = (
    "I can’t help with personal identification numbers, account details, or other sensitive data. "
    "Please don’t share PAN, Aadhaar, or similar information in chat. "
    "For investor education, use the official link below."
)

ABSTENTION_LOW_CONTEXT_TEXT = (
    "I couldn’t find enough relevant information in the indexed sources to answer that precisely. "
    "Try rephrasing or check the official resources below."
)

GENERATION_JSON_INSTRUCTION = """You are a facts-only assistant for Indian mutual funds.

Hard rules:
- Use ONLY the CONTEXT blocks below for factual claims. If context is insufficient, say so briefly in answer_text and still set citation_url to the most relevant source_url from context, or use the first context block's source_url.
- At most THREE sentences in answer_text.
- No investment advice, no fund comparisons, no "better/worse", no predicted returns.
- Output a single JSON object with exactly these keys:
  "answer_text" (string),
  "citation_url" (string, must equal one of the source_url values listed in CONTEXT),
  "last_updated" (string, ISO date YYYY-MM-DD if you can infer from fetched_at in CONTEXT, else empty string).

Do not include markdown fences or any text outside the JSON object."""
