# Add Skeleton Loading to Screen

Add skeleton loading to the screen at `$ARGUMENTS` following the project's established pattern.

---

## Core principle

**One widget, two data sources. Zero ternaries in the widget tree.**

The skeleton and the real view use the **exact same widget**. The difference is resolved *before* the widget tree via two variables:

| Variable | Purpose |
|----------|---------|
| `displayState` | Real state when loaded, mockup state when skeleton |
| `callbacks` | Real callbacks when loaded, no-ops when skeleton |

Both are derived via a single `switch (isSkeletonLoading)` at the top of `build()`. The widget tree below is clean — no `? :` operators, no `if/else` branches.

```dart
// ✅ CORRECT — all branching before the tree
final displayState = isSkeletonLoading ? _skeletonState : state;
final callbacks = switch (isSkeletonLoading) {
  true  => (onTap: () {}, onChanged: (String _) {}),
  false => (
    onTap: () => _doRealThing(context),
    onChanged: (String v) => notifier.onChange(v),
  ),
};

MyWidget(data: displayState.items, onTap: callbacks.onTap)

// ❌ WRONG — ternaries scattered in the widget tree
MyWidget(
  data: isSkeletonLoading ? mockup : state.items,
  onTap: isSkeletonLoading ? () {} : () => _doRealThing(context),
)

// ❌ WRONG — two separate skeleton/real widgets
if (isSkeletonLoading) _SkeletonBody() else _RealBody(state)
```

---

## Steps

### 1. Analyze the target screen

Read the page file and its provider/state to understand:
- What data is being loaded (list, object, etc.)
- The exact model types used
- Which widgets render the loaded data and which callbacks they need
- Whether any widgets use `AppCacheImage` or `NetworkImage` (requires special handling)

### 2. Create mockup data in `lib/core/config/app_mockup.dart`

Append a `const` list/object at the **end** of the file using the **same model** the screen renders.

**Use `BoneMock` for realistic placeholder text** — it generates correctly-shaped strings that give the skeleton natural proportions:

```dart
import 'package:skeletonizer/skeletonizer.dart';

// In app_mockup.dart — append at end
final myFeatureMockup = List.filled(
  4,
  MyModel(
    id: 'skeleton',
    name: BoneMock.name,           // realistic name length
    description: BoneMock.words(5), // ~5-word sentence
    email: BoneMock.email,
    date: BoneMock.date,
    amount: '1,000.00',            // numbers: hardcode a realistic value
  ),
);
```

> `List.filled(n, item)` is preferred over repeating items manually — shorter and scales by changing one number.

> `BoneMock` fields: `.name`, `.email`, `.date`, `.words(n)` — use these instead of hardcoded placeholder strings like `'Placeholder Name'`.

### 3. Declare `_skeletonState` at file level

Create a pre-built fake state outside the class (avoids recreating every rebuild):

```dart
// Top of page file, outside the class
final _skeletonState = MyFeatureState(
  items: myFeatureMockup,
  balance: '1,000.00',
);
```

### 4. Derive `isSkeletonLoading`, `displayState`, and `callbacks` in `build()`

```dart
// Only true on first load — not during pull-to-refresh
final isSkeletonLoading = state.isLoading && state.items.isEmpty;

// Data resolved once
final displayState = isSkeletonLoading ? _skeletonState : state;

// Callbacks resolved once — no-ops during skeleton
final callbacks = switch (isSkeletonLoading) {
  true => (
      onItemTap: () {},
      onValueChanged: (String _) {},
    ),
  false => (
      onItemTap: () => _handleTap(context, ref, state),
      onValueChanged: (String v) => notifier.onValueChanged(v),
    ),
};
```

### 5. Wrap with `SkeletonContainer` and use Skeleton annotations

Import:
```dart
import 'package:fg_zamna_wallet/shared/widgets/skeleton/skeleton_container.dart';
import 'package:fg_zamna_wallet/core/config/app_mockup.dart';
import 'package:skeletonizer/skeletonizer.dart'; // for annotations
```

Wrap only the content area (not AppBar or fixed bottom bars):

```dart
SkeletonContainer(
  isSkeletonLoading: isSkeletonLoading,
  child: Column(
    children: [
      MyWidget(items: displayState.items, onTap: callbacks.onItemTap),
    ],
  ),
)
```

#### Skeleton annotations — apply where needed

| Situation | Annotation | Example |
|-----------|-----------|---------|
| `AppCacheImage` / `NetworkImage` | `Skeleton.replace(width, height)` | Avatar, token icon |
| Static icon that should not shimmer | `Skeleton.ignore` | Decorative `Icon(Icons.arrow_forward)` |
| Widget that should show but not animate | `Skeleton.keep` | Status badge with fixed color |
| Container that should act as one bone | `Skeleton.leaf` | Entire card shimmers as one block |
| Multiple small adjacent bones → one | `Skeleton.unite` | Icon + label pair |
| `CustomPainter` widget | `Skeleton.shade` | Chart, gauge |

```dart
// AppCacheImage always needs Skeleton.replace — empty URL causes errors
Skeleton.replace(
  width: 40,
  height: 40,
  child: AppCacheImage(url: token.iconUrl, width: 40, height: 40),
)

// Decorative chevron — should not shimmer
Skeleton.ignore(
  child: Icon(Icons.keyboard_arrow_down),
)

// Card treated as a single bone block
Skeleton.leaf(
  child: Container(
    decoration: BoxDecoration(...),
    child: ListTile(...),
  ),
)

// Row of icon + label unified into one bone
Skeleton.unite(
  child: Row(
    children: [
      Icon(Icons.star),
      SizedBox(width: 4),
      Text(label),
    ],
  ),
)
```

### 6. Ensure `isLoading` is in the Freezed state

```dart
@freezed
class MyFeatureState with _$MyFeatureState {
  const factory MyFeatureState({
    @Default([]) List<MyModel> items,
    @Default(false) bool isLoading,
  }) = _MyFeatureState;
}
```

In the notifier, toggle around the async call:

```dart
Future<void> loadData() async {
  state = state.copyWith(isLoading: true);
  try {
    final result = await _repository.getData();
    state = state.copyWith(items: result, isLoading: false);
  } catch (e) {
    state = state.copyWith(isLoading: false);
  }
}
```

### 7. (Optional) Enable switch animation

Add `enableSwitchAnimation: true` to `SkeletonContainer` (or directly on `Skeletonizer`) for a smooth fade when transitioning from skeleton to real content:

```dart
// In SkeletonContainer — or update the wrapper to expose this param
Skeletonizer(
  enabled: isSkeletonLoading,
  enableSwitchAnimation: true,
  child: ...,
)
```

### 8. Run code generation if needed

If any model or state was modified:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

---

## Quick reference: skeletonizer API

```dart
// Annotations
Skeleton.ignore(child: ...)        // skip entirely
Skeleton.keep(child: ...)          // show as-is, no animation
Skeleton.shade(child: ...)         // shader only (CustomPainter)
Skeleton.replace(w, h, child: ...) // swap with placeholder (NetworkImage)
Skeleton.leaf(child: ...)          // whole container = one bone
Skeleton.unite(child: ...)         // merge adjacent bones into one

// Manual bones (Skeletonizer.zone only)
Bone(width: 80, height: 16)
Bone.circle(size: 40)
Bone.text(words: 2)
Bone.multiText(lines: 3)
Bone.icon()
Bone.button()

// Mock data helpers
BoneMock.name          // 'John Smith'
BoneMock.email         // 'john@example.com'
BoneMock.date          // 'Jan 1, 2024'
BoneMock.words(n)      // n random words

// Check state inside child
Skeletonizer.of(context).enabled
```

---

## Checklist before finishing

- [ ] Mockup data appended at end of `app_mockup.dart`, uses `List.filled()` + `BoneMock`
- [ ] `_skeletonState` declared at file level (not inside `build()`)
- [ ] `isSkeletonLoading` uses `state.isLoading && state.<items>.isEmpty`
- [ ] `displayState` and `callbacks` both derived via `switch (isSkeletonLoading)`
- [ ] Widget tree has **zero ternaries** — all branching done before the tree
- [ ] No separate skeleton widget — same widget for both states
- [ ] `AppCacheImage` / `NetworkImage` wrapped with `Skeleton.replace`
- [ ] Purely decorative icons wrapped with `Skeleton.ignore`
- [ ] `SkeletonContainer` wraps only content area, not AppBar or fixed bars
- [ ] `isLoading` toggled correctly in notifier (true before, false in both success and error)
- [ ] `build_runner` run if state/models were modified
- [ ] `flutter analyze` passes with no errors
