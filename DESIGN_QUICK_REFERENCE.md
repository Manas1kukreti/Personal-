# LedgerFlow Design System - Quick Reference

## 🎨 Colors at a Glance

| Name | Hex | Usage |
|------|-----|-------|
| Primary | `#0d6e56` | Buttons, active states, accents |
| Primary Hover | `#0a5a46` | Button hover state |
| Background | `#f4f7f6` | Page background |
| Surface | `#ffffff` | Cards, panels, inputs |
| Surface Alt | `#f7faf9` | Form panels, right pane |
| Border | `#c4ddd6` | Component borders |
| Border Light | `#eef4f2` | Subtle dividers (table rows) |
| Text Primary | `#0a3d2e` | Headings, values |
| Text Secondary | `#6b9080` | Labels, metadata |
| Text Muted | `#8ab8aa` | Placeholders, footer notes |
| Success | `#0f6e56` | Approved status |
| Warning | `#854f0b` | Pending status |
| Danger | `#a32d2d` | Failed/Declined status |
| Info | `#185fa5` | Initiated status |
| Highlight | `#e1f5ee` | Icon backgrounds |
| Tab Bg | `#e8f3ef` | Inactive tab strip |

## 🧩 Component Quick Build

### Primary Button
```jsx
<button className="primary-button">
  <FiCheck /> Save Changes
</button>
```
**CSS**: Teal bg, white text, 9px radius, 9px 16px padding

### Secondary Button
```jsx
<button className="secondary-button">
  <FiX /> Cancel
</button>
```
**CSS**: Teal border, transparent bg, hover to teal-50

### Input with Label
```jsx
<label style={{ display: "block" }}>
  <span style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#3a6655", marginBottom: 4 }}>
    Email Address
  </span>
  <input className="form-input" placeholder="name@example.com" />
</label>
```

### Card/Panel
```jsx
<div className="elevated-panel p-5">
  <h2 style={{ fontSize: 14, fontWeight: 500, color: "#0a3d2e" }}>
    Section Title
  </h2>
  <p style={{ fontSize: 13, color: "#6b9080" }}>
    Description
  </p>
</div>
```

### Status Pill
```jsx
const statusColors = {
  approved: { bg: "#e1f5ee", color: "#0f6e56" },
  pending: { bg: "#faeeda", color: "#854f0b" },
  declined: { bg: "#fcebeb", color: "#a32d2d" }
};

const config = statusColors[status];
<span style={{
  background: config.bg,
  color: config.color,
  padding: "4px 8px",
  borderRadius: 4,
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  fontSize: 11,
  fontWeight: 500
}}>
  <span style={{
    width: 4, height: 4,
    borderRadius: "50%",
    background: config.color
  }} />
  {status}
</span>
```

### Table
```jsx
<div className="elevated-panel overflow-hidden">
  <table style={{ width: "100%", borderCollapse: "collapse" }}>
    <thead>
      <tr style={{ background: "#f4f7f6", borderBottom: "0.5px solid #c4ddd6" }}>
        <th style={{ padding: "10px 12px", fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6b9080" }}>Column</th>
      </tr>
    </thead>
    <tbody>
      <tr style={{ borderBottom: "0.5px solid #eef4f2" }}>
        <td style={{ padding: "10px 12px", color: "#0a3d2e" }}>Data</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Filter Pill
```jsx
<button
  onClick={() => setFilter(type)}
  style={{
    padding: "6px 12px",
    borderRadius: 6,
    border: "0.5px solid",
    fontSize: 11,
    fontWeight: 500,
    background: activeFilter === type ? "#0d6e56" : "#f4f7f6",
    color: activeFilter === type ? "#fff" : "#0a3d2e",
    borderColor: activeFilter === type ? "#0d6e56" : "#c4ddd6",
    cursor: "pointer"
  }}
>
  {type}
</button>
```

## 📝 Typography Quick Reference

```jsx
// Page Title
<h1 style={{ fontSize: 20, fontWeight: 500, color: "#0a3d2e" }}>
  Page Title
</h1>

// Section Title
<h2 style={{ fontSize: 14, fontWeight: 500, color: "#0a3d2e" }}>
  Section Title
</h2>

// Body Text
<p style={{ fontSize: 13, color: "#1a3a2e" }}>
  Body text content
</p>

// Label
<span style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#3a6655", letterSpacing: "0.06em" }}>
  LABEL TEXT
</span>

// Meta/Small
<p style={{ fontSize: 11, color: "#6b9080" }}>
  Meta information
</p>

// Monospace (IDs, amounts)
<span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 500 }}>
  TXN_12345
</span>
```

## 🎬 Animation Quick Reference

```jsx
// Slide in from top on load
<div className="animate-slide-in-top">Content</div>

// Fade in and scale up
<div className="animate-fade-in-scale" style={{ animationDelay: "0.2s" }}>Content</div>

// Staggered entrance
<div style={{ animation: "staggerIn 0.4s ease-out 0.1s both" }}>Item 1</div>
<div style={{ animation: "staggerIn 0.4s ease-out 0.15s both" }}>Item 2</div>
<div style={{ animation: "staggerIn 0.4s ease-out 0.2s both" }}>Item 3</div>

// Hover elevation
onMouseEnter={(e) => {
  e.target.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.08)";
  e.target.style.transform = "translateY(-2px)";
}}
onMouseLeave={(e) => {
  e.target.style.boxShadow = "none";
  e.target.style.transform = "translateY(0)";
}}
```

## 📐 Spacing Quick Reference

```jsx
// Page wrapper
<div style={{ padding: "24px 28px" }}>

// Section spacing
<section style={{ gap: 20, display: "grid" }}>

// Card padding
<div style={{ padding: "16px 20px" }}>

// Table cell
<td style={{ padding: "10px 12px" }}>

// Button padding
<button style={{ padding: "9px 16px" }}>

// Input padding
<input style={{ padding: "9px 12px 9px 36px" }}>  /* Left icon space */
```

## 🎯 Common Patterns

### KPI Card
```jsx
<div className="elevated-panel p-4">
  <div style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6b9080" }}>
    METRIC LABEL
  </div>
  <div style={{ marginTop: 12, fontSize: 20, fontWeight: 500, color: "#0a3d2e" }}>
    1,234
  </div>
  <div style={{ marginTop: 8, fontSize: 11, color: "#6b9080" }}>
    +12% vs last week
  </div>
</div>
```

### Empty State
```jsx
<div style={{
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 256,
  borderWidth: "0.5px",
  borderColor: "#c4ddd6",
  background: "#f4f7f6",
  fontSize: 13,
  color: "#6b9080",
  borderRadius: 8
}}>
  No data to display
</div>
```

### Info Tile
```jsx
<div style={{
  borderWidth: "0.5px",
  borderColor: "#c4ddd6",
  background: "#f4f7f6",
  borderRadius: 8,
  padding: 12
}}>
  <div style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", color: "#6b9080" }}>
    Label
  </div>
  <div style={{ marginTop: 4, fontSize: 13, fontWeight: 500, color: "#0a3d2e" }}>
    Value
  </div>
</div>
```

### Form Error
```jsx
{error && (
  <div style={{
    borderWidth: "0.5px",
    borderColor: "#a32d2d",
    background: "#fcebeb",
    borderRadius: 8,
    padding: 12,
    fontSize: 13,
    color: "#a32d2d",
    display: "flex",
    gap: 8,
    alignItems: "flex-start"
  }}>
    <FiAlertCircle style={{ flexShrink: 0 }} />
    <span>{error}</span>
  </div>
)}
```

## 🚀 Pro Tips

1. **Use Inline Styles for One-Offs** - For unique styling not in `.css`
2. **Combine Classes with Inline Styles** - `className="elevated-panel p-5"` + custom style
3. **Reuse Component Snippets** - Copy-paste the patterns above
4. **Animate on Load** - Add `animate-slide-in-top` or `animate-fade-in-scale`
5. **Color Consistency** - Always use hex values from the palette table
6. **Typography Consistency** - Follow the typography quick reference
7. **Spacing** - Use multiples of 4px (8, 12, 16, 20, 24, 28...)
8. **Hover Effects** - Elevation + transform translateY(-2px) for cards

## 📱 Responsive Breakpoints

- **Mobile**: Default (no breakpoint)
- **Tablet**: `md:` (640px+)
- **Desktop**: `lg:` (1024px+)
- **Large**: `xl:` (1280px+)

Example:
```jsx
<section style={{ 
  display: "grid", 
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: 16 
}}>
  {items.map(item => <Card key={item.id} />)}
</section>
```

---

**Last Updated**: May 2026  
**Version**: 1.0  
**Compliance**: ✅ Production Ready
