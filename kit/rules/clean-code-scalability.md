# Clean Code & Scalability Rules — FG Zamna Wallet

Rules derived from static analysis of the actual codebase. All agents and reviewers must enforce these on every file touched.

---

## Widget Rules

**W1. One screen, one file — split beyond 200 lines.**
If a `*_page.dart` exceeds ~200 lines, extract sub-sections into named private widget classes or separate files in the same feature folder. Page files must read like a composition of named pieces, not a single monolithic `build` method. Reviewers must flag any page file exceeding 300 lines without justification.

**W2. Use `HookConsumerWidget` for screens, `ConsumerWidget` for pure display widgets.**
- Screens needing `useEffect`, `useTextEditingController`, or local animation controllers → `HookConsumerWidget`
- Pure display widgets that only receive data via parameters and call callbacks → `ConsumerWidget` or `StatelessWidget`
- Never mix `useState` local state with business logic in the same widget.

**W3. Never use `ref.read(provider)` for reactive display.**
`ref.read` is for one-time actions (button tap, `useEffect` init). Any value rendered in the widget tree must come from `ref.watch`. Reject patterns where a rendered value is accessed through `ref.read` to skip a rebuild.

**W4. Never pass `BuildContext` into a provider method.**
Passing `BuildContext` for navigation or snackbars creates an implicit widget lifecycle dependency and forces `// ignore: use_build_context_synchronously`. Instead, surface error state through a Freezed state field (e.g. `errorMessage`) and handle display in the widget via `useEffect` or `ref.listen`.

**W5. Do not use `setState` for data that lives in a provider.**
Local `setState` is only acceptable for pure UI concerns (e.g. `_currentIndex` for tabs) with no business logic attached. State with business meaning must live in Riverpod.

**W6. Use `const` on every leaf widget that does not depend on runtime data.**
Enforce `prefer_const_constructors` in `analysis_options.yaml`. Reviewers must reject `new SizedBox()`, `new Padding()`, or similar where all arguments are literal values.

**W7. Wrap independently-animated or scrolling subtrees in `RepaintBoundary`.**
Large list items (token rows, transaction rows) that contain price-update animations must be wrapped in `RepaintBoundary` to prevent full-list repaints on partial data changes.

---

## State Management Rules

**S1. Every notifier must have a paired `*_state.dart` with a `@freezed` state class.**
No inline maps, `Map<String, dynamic>` state, or bare primitive-typed `Notifier`. Files must be co-located in the feature folder. Only truly app-global state (auth, notifications) belongs in `lib/core/providers/`.

**S2. Notifier instance fields must not be used as sync flags between state fields.**
Mutable boolean instance flags like `_isUpdatingFromAmount` are fragile across notifier re-creations. Replace with a dedicated field in the Freezed state, or restructure so one field is always derived from the other.

**S3. Methods that produce navigation params must return a typed Freezed class, never `Map<String, dynamic>`.**
Create dedicated params classes (e.g. `ConfirmSendParams`) in `lib/models/params/` and pass them as GoRouter `extra`. Never cast an untyped map on the receiving page. Follow the `ConfirmSwapParams` pattern already in the project.

**S4. Never call `getIt<X>()` inside notifier methods.**
This bypasses the DI graph and makes the notifier untestable. Repositories must be accessed by reading a Riverpod provider or injected at construction time via the `@riverpod` `build` argument pattern.

**S5. `Future.microtask(() => init())` inside `build()` requires a `ref.mounted` guard and a comment.**
This pattern is permitted for triggering async work on notifier creation, but every such call must check `if (!ref.mounted) return;` as the first line of the async body and must include a comment explaining the intent. Reject silent fire-and-forget without mounted guards.

**S6. Never expose repository or service instances as public getters on a notifier.**
Internal collaborators must be private. If a sibling notifier needs data from another notifier, it reads it via `ref.read(otherProvider)`.

---

## Repository and Service Rules

**R1. Apply Interface Segregation — abstract interfaces must declare only what the domain requires.**
If send and swap require different subsets of methods, define `ISignable` and `ISwappable` sub-interfaces rather than growing a single base repository with every variant.

**R2. Repository files must contain only the abstract interface and its `*Impl` class.**
Crypto utility functions belong in `lib/core/crypto/`. Constants belong in `lib/core/config/` or `lib/models/`. Top-level functions in repository files are forbidden.

**R3. Repository methods that can fail must return a typed result — never swallow exceptions and return `null`.**
Callers cannot distinguish "no data exists" (expected) from "JSON decode failed" (bug) when both return `null`. Define domain-specific exception types or use a `Result<T, E>` wrapper.

**R4. `SendHandlerFactory` must be a `@lazySingleton`, not a static method.**
Static factories are untestable and bypass DI. Register it as a GetIt singleton and inject it into the notifier.

**R5. `BaseSendHandler` must not call `getIt` — inject repositories at construction time.**
The factory already has access to the DI container; pass dependencies into the handler constructor at creation time.

**R6. All DI registrations must use `@injectable` / `@lazySingleton` annotations.**
Manual registration in `di.dart` is reserved only for classes requiring async `await` during setup (e.g. `AppLocalStorage.create()`). Dual-registration of the same class is forbidden.

---

## Navigation and Routing Rules

**N1. Route path strings must be `const` on `AppRouter` — never inline literals at call sites.**
All navigation calls must reference `AppRouter.sendToken`, `AppRouter.confirmSend`, etc. Reject any string literal route path not referencing the `AppRouter` constant.

**N2. GoRouter `extra` parameters must be typed Freezed objects, not `Map<String, dynamic>`.**
The `Map<String, dynamic>` pattern in `route_config.dart` is deprecated. All new routes must use typed params classes. Do not introduce map-based extras.

**N3. Route fallback error widgets must use a shared `AppErrorPage` widget.**
Do not repeat `Scaffold(body: Center(child: Text(...)))` inline across multiple routes. Extract to `lib/shared/widgets/app_error_page.dart`.

**N4. Never use `S.current` inside `route_config.dart`.**
`S.current` accesses the last-built locale, not the context locale. Use `S.of(context)` or `context.l10n` where a valid `BuildContext` is available.

---

## File and Folder Rules

**F1. Every feature folder must have exactly one provider, one state, and one page file at the feature root.**
Sub-flows live in sub-folders (e.g. `confirm_send/`). Extracted helper widgets live in a `widgets/` sub-folder. No utilities or extensions at feature root level.

**F2. Generated files (`*.freezed.dart`, `*.g.dart`) must never be manually edited.**
Any hand-written logic or `// TODO` in a generated file is an immediate rejection. The annotated source file is always the source of truth.

**F3. Enums must live in `lib/models/enums/` — never declared inline in a state or page file.**
Domain enums referenced by both repositories and notifiers must not live inside feature state files.

**F4. Localisation-aware extension methods must not live inside the models layer.**
Extensions on enums that depend on `BuildContext` are UI-layer concerns. Place them in a `*_ext.dart` file co-located with the enum.

**F5. `lib/repositories/` barrel files must only re-export the abstract interface, never the implementation.**
`WalletRepositoryImpl` is wired only through DI. Callers import the abstract type only, enforcing dependency inversion at the import boundary.

---

## Performance Rules

**P1. Never call `SharedPreferences.getInstance()` directly inside a repository method.**
All storage access must go through `AppLocalStorage` and `AppSecureStorage`, which are injected and pre-initialised at startup.

**P2. Token/transaction lists must use `ListView.builder` or `SliverList` — never `Column` with a mapped list.**
`children: items.map((e) => Widget(e)).toList()` builds all items eagerly. Reject `Column`-based lists with more than a handful of statically-known items.

**P3. Price and balance values that update on a timer or stream must be isolated in a leaf `ConsumerWidget`.**
Extract `PortfolioBalanceWidget` as a separate `ConsumerWidget` that watches only the balance slice. Prevents the full token list from rebuilding on every price tick.

**P4. `useEffect` dependencies must be minimal and explicit.**
A `useEffect` depending on the full state object fires on every state mutation. Depend only on the specific fields being synced (e.g. `[state.amount, state.recipientAddress]`).

**P5. Replace sequential `await` chains with `Future.wait` when calls are independent.**
Any two or more independent `await` calls in sequence must be reviewed and converted to `Future.wait` unless there is a documented data dependency between them.

---

## Security Rules (Crypto Wallet Specific)

**SE1. Methods that accept or return a mnemonic, seed, or private key as a plain `String` must be annotated with `// SECURITY: sensitive`.**
Makes security-sensitive data flows discoverable in code review. Applies to method signatures in the repository interface and every caller.

**SE2. Decrypted passphrases must never be stored in Riverpod state.**
Pass the decrypted passphrase as a method argument directly to the signing call. It must never appear as a field on a Freezed state class.

**SE3. User-facing error fields must map to localised strings only — never `error.toString()`.**
Raw exception messages may contain internal addresses, keys, or stack details. Pass raw error text only to the logger and Sentry, never into state that surfaces to the UI.
