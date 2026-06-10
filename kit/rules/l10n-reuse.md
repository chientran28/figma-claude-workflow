# L10n Key Reuse — No Duplicate String Values

**Rule:** Before adding a new localisation key, search all existing ARB files for a key with the same English value. If one exists, reuse that key — do not declare a new one.

**Why:** Duplicate keys inflate the ARB files, increase translation cost, and cause inconsistency when the shared concept is updated in one place but not the other.

---

## How to check before adding

1. Search the English source file for the intended value:
   ```bash
   grep -n '"Your new string"' lib/l10n/intl_en.arb
   ```
2. If found, copy the existing key name and use it in Dart.
3. If not found, append the new key at the **end** of all 4 ARB files (see coding-standards rule §3).

---

## Canonical keys to reuse (most commonly duplicated)

| Value (EN) | Canonical key |
|---|---|
| `"Cancel"` | `button_cancel` |
| `"Confirm"` | `button_confirm` |
| `"Try Again"` | `button_retry` |
| `"Copied"` | `button_copied` |
| `"Failed"` | `failed` |
| `"Balance"` | `balance` |
| `"From"` | `from` |
| `"To"` | `to` |
| `"Search token"` | `search_token` |
| `"No tokens found"` | `no_tokens_found` |
| `"Invalid amount"` | `error_invalid_amount` |
| `"Insufficient balance"` | `error_insufficient_balance` |

---

## Enforcement

Reviewers must reject any new ARB key whose English value already exists under a different key. The rule applies to all 4 language files (`intl_en.arb`, `intl_es.arb`, `intl_ja.arb`, `intl_zh.arb`).
