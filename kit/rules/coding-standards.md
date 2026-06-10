# Coding Standards

Project-wide coding rules that all agents and Claude Code must enforce on every file touched.

---

## 1. No Deeply Nested Conditionals

**Rule:** `if/else` nesting must never exceed **3 levels** deep.

**Why:** Deep nesting makes logic hard to follow, test, and maintain.

**Preferred patterns:**
- **Early return / guard clause** — validate and return at the top, keep the happy path flat
- **Extract to a method** — pull nested logic into a named private method
- **Switch expression** — use Dart's `switch` expression for multi-branch logic

```dart
// BAD — 4 levels deep
if (user != null) {
  if (user.isActive) {
    if (wallet != null) {
      if (wallet.balance > 0) {
        // do something
      }
    }
  }
}

// GOOD — guard clauses flatten the logic
if (user == null) return;
if (!user.isActive) return;
if (wallet == null) return;
if (wallet.balance <= 0) return;
// do something
```

---

## 2. No Hardcoded User-Facing Strings

**Rule:** Any string displayed to the user **must not** be hardcoded in Dart source files. Declare it in the l10n `.arb` files instead.

**L10n files:**
- `lib/l10n/intl_en.arb` — English (source of truth)
- `lib/l10n/intl_es.arb` — Spanish
- `lib/l10n/intl_ja.arb` — Japanese
- `lib/l10n/intl_zh.arb` — Chinese

**Usage in Dart:**
```dart
// BAD
Text('Send Token')

// GOOD
Text(context.l10n.sendToken)
// or via S.of(context).sendToken
```

After adding a new key, run:
```bash
flutter pub run intl_utils:generate
```

---

## 3. New String Keys Must Be Appended at the End of the ARB File

**Rule:** When adding a new localisation key, always add it at the **end** of the `.arb` file — never insert it in the middle.

**Why:** Keeps diffs clean, avoids merge conflicts, and makes code review easier.

```jsonc
// intl_en.arb — add new keys here, after all existing keys
{
  "existingKey": "Existing value",
  // ... all current keys ...

  "myNewKey": "My new string"   // ← always append at the bottom
}
```

The same key must be added to **all language files** (`intl_en.arb`, `intl_es.arb`, `intl_ja.arb`, `intl_zh.arb`).

---

## 4. Always Use Typed Models — Never Dynamic Map Access

**Rule:** Never access data through dynamic maps using string keys like `data["abc"]` or `json["key"]`. Always declare a typed **Freezed model** and deserialize properly.

**Why:** String-key access is untyped, unrefactorable, and silently breaks at runtime.

```dart
// BAD — brittle, no type safety
final name = data["user"]["name"];
final balance = response["balance"];

// GOOD — declare a Freezed model
@freezed
class UserProfile with _$UserProfile {
  const factory UserProfile({
    required String name,
    required String email,
  }) = _UserProfile;

  factory UserProfile.fromJson(Map<String, dynamic> json) =>
      _$UserProfileFromJson(json);
}

// Then deserialize
final profile = UserProfile.fromJson(data);
final name = profile.name;
```

All models live in `lib/models/` and must use `@freezed`. Run `build_runner` after creating or modifying models:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```
