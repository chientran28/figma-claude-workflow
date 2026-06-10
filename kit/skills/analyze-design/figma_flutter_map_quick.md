# Figma → Flutter Quick Map (basics)
> Exotic / unusual constructs → `FIGMA_FLUTTER_MAP.md` · Implementation recipes → `.ui-workspace/flutter_helper_design.md`

## Node Type → Widget

| Figma | Flutter |
|-------|---------|
| FRAME, HORIZONTAL auto-layout | `Row` |
| FRAME, VERTICAL auto-layout | `Column` |
| FRAME, no layout / absolute children | `Stack` |
| FRAME, has fill / radius / border | `Container(decoration: BoxDecoration(...))` |
| FRAME, clipsContent | `ClipRRect(borderRadius:..., child:...)` |
| FRAME, scroll vertical | `SingleChildScrollView` |
| TEXT | `Text('...', style: TextStyle(...))` |
| RECTANGLE, fill SOLID | `Container(color: AppColors.xxx)` |
| RECTANGLE, fill GRADIENT_LINEAR | `Container(decoration: BoxDecoration(gradient: LinearGradient(...)))` |
| RECTANGLE, fill IMAGE | `Image.asset(..., fit: BoxFit.cover)` |
| RECTANGLE, no fill | `SizedBox(width: w, height: h)` |
| ELLIPSE | `Container(decoration: BoxDecoration(shape: BoxShape.circle))` |
| VECTOR / BOOLEAN_OPERATION | `SvgPicture.asset(...)` |
| LINE | `Divider()` |
| GROUP | `Stack` |
| INSTANCE | reuse mapped widget |
| COMPONENT | `StatelessWidget` |

## Auto-layout

| Figma | Flutter |
|-------|---------|
| `layoutMode: HORIZONTAL/VERTICAL/NONE` | `Row` / `Column` / `Stack` |
| `itemSpacing: N` | `SizedBox(width/height: N)` between children |
| `primaryAxisAlignItems: MIN/CENTER/MAX/SPACE_BETWEEN` | `MainAxisAlignment.start/center/end/spaceBetween` |
| `counterAxisAlignItems: MIN/CENTER/MAX/STRETCH` | `CrossAxisAlignment.start/center/end/stretch` |
| `layoutSizingHorizontal/Vertical: FILL` | `Expanded` |
| `layoutGrow: 1` | `Expanded` |
| `padding` | `EdgeInsets.fromLTRB(l, t, r, b)` |

## Fill / Stroke / Corner

| Figma | Flutter |
|-------|---------|
| `fills: SOLID` | `color: AppColors.xxx` — never hardcode hex |
| `fills: GRADIENT_LINEAR` | `LinearGradient(begin:, end:, colors:, stops:)` |
| `fills: IMAGE` | `DecorationImage(image: AssetImage(...), fit: BoxFit.cover)` |
| `strokes: SOLID` | `Border.all(color:, width:)` |
| `cornerRadius: N` | `BorderRadius.circular(N)` |
| `rectangleCornerRadii` | `BorderRadius.only(...)` |

## Text

| Figma | Flutter |
|-------|---------|
| `fontSize / fontWeight / letterSpacing` | `TextStyle(fontSize:, fontWeight:, letterSpacing:)` |
| `lineHeightPx` | `TextStyle(height: lineHeightPx / fontSize)` |
| `textAlignHorizontal` | `TextAlign.left/center/right` |
| `textCase: UPPER` | `.toUpperCase()` |
| `textTruncation: ENDING` | `overflow: TextOverflow.ellipsis` |

## Basic Effects

| Figma | Flutter |
|-------|---------|
| `DROP_SHADOW` | `BoxShadow(color, blurRadius, spreadRadius, offset)` |
| `opacity < 1.0` (node-level) | `Opacity(opacity: N)` — prefer `Color.withOpacity(N)` for color-only |
