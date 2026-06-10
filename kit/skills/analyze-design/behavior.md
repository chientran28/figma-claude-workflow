# Mobile Screen Behavior Reference

Identify the screen type first → then read only that section.

## Identify screen type
| Signal in Figma / task | Type |
|--|--|
| In bottom navbar; no back button | **A — Main (`go`)** |
| Opened by tap/button; back arrow in AppBar | **B — Push (`push`)** |
| Partial overlay sliding from bottom | **C — Bottom Sheet** |
| Center overlay + backdrop; confirm/alert/2-option | **D — Dialog** |

---

## A — Main Screen (GoRouter `go`)
> Bottom-navbar root. No back button. State persists across tab switches.

**Base:** `SafeArea` body · always scrollable (`SingleChildScrollView`/`CustomScrollView`, never bare
`Column`) · no back button (`automaticallyImplyLeading:false` or no AppBar) · preserve tab state
(`IndexedStack`/`AutomaticKeepAliveClientMixin`).

| Pattern (signal) | Flutter |
|--|--|
| Vertical scroll | `SingleChildScrollView(physics: BouncingScrollPhysics())` |
| Lazy list (repeated rows) | `ListView.builder` — never `Column + .map()` |
| Pull-to-refresh (refresh icon) | `RefreshIndicator` |
| Sticky / collapsing header | `CustomScrollView` + `SliverAppBar(pinned:true)` |
| Horizontal chips wider than screen | `SingleChildScrollView(scrollDirection: Axis.horizontal)` |
| Row/card with `›` → detail | `onTap: context.push(route, extra: TypedParams())` |
| Tabs | `TabBar`+`TabBarView` or `IndexedStack` |
| Re-tap active tab → scroll top | `ScrollController.animateTo(0)` |
| Copy icon | `Clipboard.setData` + transient `SnackBar` |
| `∨` accordion / FAQ | `ExpansionTile` / `AnimatedCrossFade` |
| Date-grouped list (headers) | `SliverList` header+item types |
| "Show more" / "View all" | push list screen OR `AnimatedContainer` inline |
| Floating button bottom-right | `FloatingActionButton` |

**States:** loading → shimmer matching shape · empty → illustration+message+optional CTA (no spinner) · error → card + Retry.

---

## B — Push Screen (GoRouter `push`)
> Detail / form / settings sub-pages. Opened via tap. Has back button.

**Base:** `AppBar` auto back (don't disable iOS swipe) · `Scaffold(resizeToAvoidBottomInset:true)` ·
typed `extra` (Freezed, never `Map<String,dynamic>`) · `PopScope` only for unsaved-data warning.

| Pattern (signal) | Flutter |
|--|--|
| Scrollable form | `SingleChildScrollView` + `Column` of fields |
| Nested inner list | `shrinkWrap:true, physics:NeverScrollableScrollPhysics()` |
| Primary CTA (Send/Confirm/Save) | `ElevatedButton` → spinner + disabled while loading |
| Long-press → menu | `GestureDetector(onLongPress:)` → sheet/menu |
| Swipe-to-delete | `Dismissible(key:, onDismissed:, background:)` |
| Toggle | `Switch`/`Checkbox(value:, onChanged:)` |
| Select 1 of N | selected-index state + `onTap` |
| Paste from clipboard | `Clipboard.getData(Clipboard.kTextPlain)` |
| QR scan (camera icon) | push camera → `context.pop(result)` |
| Clear `×` | `suffixIcon: value.isNotEmpty ? clear : null` |
| Show/hide password (eye) | `obscureText` toggled by `IconButton` |
| Numeric / PIN pad | `keyboardType: TextInputType.number` or digit grid |
| Search + debounce | `Timer(300ms)` reset per keystroke |
| Form validation | inline error below field — not `SnackBar` |

**States:** action loading → button spinner+disabled · success → navigate away / transient `SnackBar` (never a blocking dialog) · error → inline (form) or `SnackBar` (action).

---

## C — Bottom Sheet
> Slides up from bottom. Content-dependent height.

**Base:** `showModalBottomSheet(isScrollControlled:true)` · `SafeArea` +
`Padding(bottom: MediaQuery.viewInsetsOf(context).bottom)` · drag handle top-center ·
`isDismissible/enableDrag:true` default; blocking → `false` + explicit close.

| Variant / pattern | Flutter |
|--|--|
| Fixed short (confirm/options) | fixed-height `Container` |
| Tall + scroll (long list, token select) | `DraggableScrollableSheet(initialChildSize:0.6, minChildSize:0.4, maxChildSize:1.0)` + `ListView.builder` |
| Full screen | `isScrollControlled:true` + `height: size.height*0.95` |
| Search in sheet | `TextField` top + filtered `ListView.builder` |
| Action list (share/copy/delete) | `ListTile` rows |
| Confirm | `Column`: title, body, `Row(Cancel, Confirm)` |

---

## D — Dialog (center modal)
> Alerts / confirms / 2-option. Not for long content.

**Base:** `showDialog` → `AlertDialog`/`Dialog` · `barrierDismissible:true` default; blocking →
`false` + explicit buttons · max 2 actions (secondary + primary) · never a scrollable list inside (use a sheet).

| Variant | Flutter |
|--|--|
| Confirm / destructive | `AlertDialog(actions:[cancel, confirm])` |
| Info / alert | `AlertDialog(actions:[ok])` |
| Custom branded | `Dialog(shape: RoundedRectangleBorder(...))` |
| Blocking loading | `Dialog(Column[CircularProgressIndicator, Text])` + `barrierDismissible:false` |

---

## Output — append `# Behavior` to the widget's block in `pre_plan.md` (after `# Layout` + `# Decoration`)
```
  # Behavior
  screen_type: A           ← A|B|C|D
  tap: row → push:TokenDetailPage · copy_btn → clipboard
  scroll: vertical · input: none · expand: none
  states: [loading:shimmer] [empty:illustration+CTA]
```
Omit any `none` field · `tap` allows multiple via ` · ` · `states` lists only visible/required states.

---

## Learned State Conventions — ASK → CONFIRM → SAVE → reuse

For any screen with data states: read `### Saved state conventions` first; a block whose `scope`
matches (its type or `all`) → apply silently. No match → ask the user once (grouped): *which states
this screen has + what each renders* → show understanding, confirm → ask *"Save as default for
<screen-type>?"* → Yes: append a block below (don't duplicate a scope); No: this screen only.
Write the result into `states:` (`# Behavior`) and `## Screen States`.

### Saved state conventions
<!-- APPEND per confirmed convention; read FIRST.
- scope: all|screen-type:A|screen-type:B|feature:<n>  loading: <shimmer|spinner>
  empty: asset:<AppSVGs.x>·text:<key>·cta:<key|none>  error: <snackbar|inline>·text:<key>·retry:<bool>  saved: <date> -->

---

## Project Scaffold Conventions (AppBar + Footer) — make-ui-plan reads + fills + reuses

Avoids re-coding AppBar/navbar/bottom on every screen. make-ui-plan reads `### Saved scaffold
conventions` first → entry for the screen's type → REUSE those widgets; no entry → find them in a
sibling of the same type, record, then reuse.

| Type | AppBar | Footer / bottom | Nav |
|---|---|---|---|
| **nav-index** (bottom-nav tab) | none / shared header | REUSE existing bottom navbar — never rebuild | `context.go` |
| **push** (action-opened) | back-button AppBar like siblings | bottom button in `SafeArea`+padding | `context.push` |

### Saved scaffold conventions
<!-- APPEND per type once real widgets found; reused by make-ui-plan.
- type: nav-index|push  appbar: <class @ lib/...|none>  footer: <navbar/button @ lib/...>  example: lib/features/<sib>/<sib>_page.dart  saved: <date> -->
