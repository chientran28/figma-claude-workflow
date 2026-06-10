# Route Naming Rules

## Step 1 — Find where routes are defined

```bash
grep -rn "static const" lib/ --include="*.dart" | grep -i "route\|router\|path" | head -20
```

Locate the class that holds route path constants (e.g. `AppRouter`, `Routes`, `AppRoute`).
Note the file path — all lookups in Step 2 target that file.

---

## Step 2 — Naming convention

- Constants are `camelCase` on the router class
- Always reference as `AppRouter.xxx` — never inline the string path at call sites
- Match the `tap: → push:XxxPage` hint to the nearest constant name
- If not found → flag `MISSING_ROUTE: AppRouter.xxx` in plan.md New Tokens table

---

## Step 3 — Navigation call

**No params** → simple call:
```dart
context.push(AppRouter.depositDetail);
```

**With params** — find the params class:
```bash
grep -rn "class.*Params" lib/models/ --include="*.dart"
```

If found → use it. If not → flag `MISSING_PARAMS: XxxParams`.
Params must be `@freezed`. Pass via `extra`:
```dart
context.push(AppRouter.depositDetail, extra: DepositDetailParams(txHash: txHash));
```

Skip params entirely if the screen receives no data.

---

## Screen type → navigation method

| Screen type | Method |
|-------------|--------|
| A (Main tab) | `context.go(AppRouter.xxx)` |
| B (Push) | `context.push(AppRouter.xxx)` |
| C (Bottom Sheet) | `showModalBottomSheet(...)` |
| D (Dialog) | `showDialog(...)` |
