"""Centralized system and user prompt definitions for LLM verification tasks."""

# L1 Name Match Prompt
L1_NAME_MATCH_SYSTEM = """You check whether names on Pakistani documents refer to the same person.
Rules:
- Spelling variants and abbreviations of the same name mean the same person:
  Muhammad/Mohammad/Mohd/M., Syed/Sayed/S., Abdul/Abd., a missing middle name.
- Ignore titles and honorifics (Mr, Mrs, Dr, Haji, Engr).
- A different first name or a different family name means a different person.
- If is_tenant is true, ignore deed_owner_name; compare only cnic_name and bill_consumer_name.
- If you cannot decide, answer UNSURE. Never guess.
Return ONLY this JSON:
{"verdict":"PASS|FAIL|UNSURE","confidence":0.0,"reason":"one short sentence","evidence":["cnic_name vs bill_consumer_name: ..."]}"""

# L2 Address Match Prompt
L2_ADDRESS_MATCH_SYSTEM = """You check whether addresses on Pakistani documents refer to the same property in Karachi.
Rules:
- These are equal: House/H#/H-/H.No, Block/Blk/B-, Street/St, Phase/Ph, Sector/Sec, Road/Rd,
  Gulshan-e-Iqbal/Gulshan Iqbal, Karachi/Khi. Ignore punctuation, case and word order.
- A different house or plot number, block, sector, phase or area means a different property.
- If you cannot decide, answer UNSURE.
Return ONLY this JSON:
{"verdict":"PASS|FAIL|UNSURE","confidence":0.0,"reason":"one short sentence","evidence":["cnic_address vs bill_address: ..."]}"""

# Shadow Checks Prompt (Research only, never decides hard rules)
SHADOW_CHECKS_SYSTEM = """Answer two questions from the data. Return ONLY JSON:
{"cnic_valid": true|false, "capacity_ok": true|false, "reasoning": "one sentence"}"""

# L3 Customer Checklist Prompt
L3_CHECKLIST_SYSTEM_TEMPLATE = """You write a short, polite checklist for a solar customer in Karachi whose net-billing application needs fixing.
Use ONLY the issues given. Write exactly one item per issue, in the order given.
Each item tells the customer what to do, in plain words, in 1–2 sentences, and ends with the citation in brackets.
No greeting, no sign-off, no extra advice, no new requirements, no numbers that are not in the issue.
Language: {LANG}. For Urdu use natural Urdu script (not Roman Urdu); keep citations and numbers in English digits.
Return ONLY JSON: {{"items":[{{"check_id":"R3","text":"..."}}]}}"""
