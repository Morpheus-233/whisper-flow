# BRIEFING — 2026-10-22T11:05:00Z

## Mission
Investigate script leakage failure modes in FastDevanagariRomanizer (style_engine.py), including missing Candra vowels, Visarga, and Zero-Width Joiner/Non-Joiner leakage, and provide exact drop-in code recommendations.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, synthesis
- Working directory: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_fix_1
- Original parent: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Milestone: Milestone 1 Round 2 Fix Investigation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT edit code directly in style_engine.py or any other project files
- Provide exact drop-in code recommendations for style_engine.py
- Write analysis in analysis.md and a self-contained handoff.md in working directory
- Notify caller via send_message when done

## Current Parent
- Conversation ID: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `tests/test_m1_round2_adversarial.py`: lines 143-210 (Candra, Visarga, ZWJ/ZWNJ, Danda)
  - `style_engine.py`: lines 77-286 (FastDevanagariRomanizer tables, transliterate_token, romanize)
  - `.agents/teamwork/challenger_m1_1/handoff.md`: observations 1.1, 1.2, 1.4
  - `.agents/teamwork/explorer_m1_fix_2/DISPATCH.md` and `explorer_m1_fix_3/DISPATCH.md`
- **Key findings**:
  - `VOWELS` omitted 'ऑ' (U+0911), 'ऍ' (U+090D), 'ॲ' (U+0972), causing them to hit fallback `else: out.append(ch)` and leak raw Devanagari.
  - Visarga ('ः' U+0903) was only present as part of 2-char string 'अः', but character loop evaluates 1-char tokens; unhandled standalone 'ः' leaked into output.
  - ZWJ (U+200D) and ZWNJ (U+200C) are non-word chars (`\w == False`) and outside `\u0900-\u097F`, so `re.split` isolated them as delimiter tokens, and line 209 returned them verbatim.
  - Pre-stripping `\u200c` and `\u200d` before tokenization and in `transliterate_token` completely prevents invisible control code leakage.
  - Token splitting regex `[^\w\u0900-\u0963\u0966-\u097F]+` correctly treats Danda (`।` U+0964) as a delimiter, allowing words to match `DEV_COMMON_WORDS` without false schwas.
- **Unexplored areas**: None within Explorer 1 scope. Explorer 2 covers `voice_profile.py` boundary regex; Explorer 3 covers `whisper_engine.py` Stage 3 contract.

## Key Decisions Made
- Multi-layer defense: Strip `\u200c`/`\u200d` in `romanize` and `transliterate_token`, plus explicit skip in the while loop.
- Support both precomposed Candra vowels ('ऑ' U+0911, 'ऍ' U+090D, 'ॲ' U+0972) and decomposed sequences ('अ' + 'ॉ', 'अ' + 'ॅ').
- Added high-frequency loan and Visarga words to `DEV_COMMON_WORDS` ('ऑप्शन', 'ऑनलाइन', 'ऑब्जेक्ट', 'ॲप', 'दुःख', 'अतः', 'पुनः').

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- analysis.md — deep dive investigation and exact code recommendations
- handoff.md — self-contained 5-component handoff report
