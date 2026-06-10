# Token Naming Rules

**Đọc `.ui-workspace/figma_config.json` trước** → lấy đường dẫn thực tế từ `project_sources` trước khi grep/define.
> Không tạo class mới. Insert trước `}` của class hiện có.

---

## A. Search Tips

> Paths lấy từ `figma_config.json → project_sources`.

```bash
# Color / Font
grep "CLR_" <project_sources.color.dart_files>       # vd: lib/core/theme/app_colors.dart
grep "FNT_" <project_sources.font.dart_files>        # vd: lib/core/theme/app_text_styles.dart

# Asset / Icon
grep "AST_" <project_sources.asset.image.dart_file>  # vd: lib/core/config/app_images.dart
grep "ICO_" <project_sources.asset.svg.dart_file>    # vd: lib/core/config/app_svgs.dart

# Widget / Asset registry
grep "WGT_" .ui-workspace/exist_design/widgets.md
grep "AST_\|ICO_" .ui-workspace/exist_design/assets.md
grep "pending" .ui-workspace/exist_design/widgets.md   # chưa build
```

---

## B. Per-Type Naming, Insert & Key Comment

### B1. Color — `AppColors` · `project_sources.color.dart_files`

- **Key prefix:** `CLR_{scope}_{semanticName}` — semantic camelCase, không hex, không số
- **Insert:** trước `}` của class `AppColors`

```dart
static const Color brandPrimary = Color(0xFF42B4FF); // CLR_brand_primary
static const LinearGradient gradientGreen = LinearGradient(...); // CLR_brand_gradientGreen
```
`CLR_color1` ❌ · `CLR_brand_primary` ✅

---

### B2. Font — `AppTextStyle` · `project_sources.font.dart_files`

- **Key prefix:** `FNT_{scope}_{usageName}` — mô tả usage, không size
- **Insert:** trước `}` của class `AppTextStyle`

```dart
static final bodyRegular = _textStyle(14, 20); // FNT_global_bodyRegular
```
`FNT_text14` ❌ · `FNT_global_bodyRegular` ✅

---

### B3. Icon SVG — `AppSVGs` · `project_sources.asset.svg.dart_file`

- **Key prefix:** `ICO_{scope}_{actionOrObject}` · Dart name: `ic` + PascalCase
- **Insert:** trước `}` của class `AppSVGs`. File vào `assets/vectors/`. Đăng ký `pubspec.yaml`.
- **Thêm vào `assets.md`:** `ICO_walletSend | assets/vectors/ic_wallet_send.svg | SVG | SendScreen`

```dart
static const icWalletSend = 'assets/vectors/ic_wallet_send.svg'; // ICO_walletSend
```

---

### B4. Image — `AppImages` · `project_sources.asset.image.dart_file`

- **Key prefix:** `AST_{scope}_{description}` · Dart name: `bg` + PascalCase hoặc camelCase mô tả
- **Insert:** trước `}` của class `AppImages`. File vào `assets/images/`. Đăng ký `pubspec.yaml`.
- **Thêm vào `assets.md`:** `AST_authOnboarding1 | assets/images/auth_onboarding_1.png | IMAGE | OnboardingScreen`

```dart
static const authOnboarding1 = 'assets/images/auth_onboarding_1.png'; // AST_authOnboarding1
```

---

### B5. Widget — `lib/features/<scope>/widgets/`

- **Key prefix:** `WGT_{scope}_{ComponentName}[_{variant}]` · Class name PascalCase
- **Tạo file mới** trong feature folder — không insert vào global class.
- **Thêm vào `widgets.md`:** `WGT_walletTokenRow | lib/features/wallet/widgets/token_row.dart | pending | HomeScreen`
- **Status:** `pending` → `done` → `deprecated` — update ngay sau khi tạo xong file.

```dart
class TokenRow extends ConsumerWidget { // WGT_walletTokenRow
```

---

## C. Quick Reference

| Token | Class | Key Prefix | Naming |
|-------|-------|-----------|--------|
| Color | `AppColors` | `CLR_scope_name` | semantic camelCase |
| Font | `AppTextStyle` | `FNT_scope_name` | usage camelCase |
| Icon | `AppSVGs` | `ICO_scope_name` | `ic` + PascalCase |
| Image | `AppImages` | `AST_scope_name` | `bg`/desc camelCase |
| Widget | feature `widgets/` | `WGT_scope_Name` | PascalCase class |

> **Workflow:** đọc `figma_config.json` → grep trước (§A) → phân loại REUSE/NEW → insert + comment key cùng dòng (§B).
