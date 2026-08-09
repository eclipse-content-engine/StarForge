# StarForge design system

## Visual direction

**Quiet orbital workshop.** StarForge uses deep neutral surfaces with a cool
cyan focus color, restrained amber warnings, thin borders, and generous spacing.
The interface should feel like a precise creative tool—not a game launcher,
terminal skin, or science-fiction prop.

## Tokens

### Color

| Role | Value | Use |
| --- | --- | --- |
| Canvas | `#0B0F17` | Application background |
| Sidebar | `#0E1420` | Stable navigation chrome |
| Surface | `#121A27` | Primary content panels |
| Raised | `#172233` | Interactive and selected surfaces |
| Border | `#263449` | Dividers and field outlines |
| Text | `#F3F7FC` | Primary content |
| Muted text | `#9DABBE` | Supporting content |
| Accent | `#66D9EF` | Focus, selection, and primary actions |
| Accent strong | `#2CBBD8` | Primary action hover |
| Warning | `#F4C66A` | Recoverable risk |
| Error | `#FF7A90` | Blocking errors |
| Success | `#72D6A0` | Completed validation and output |

Color never carries meaning alone; statuses include labels and icons or shape.

### Typography

- Interface: Segoe UI with system fallbacks.
- Technical values: Cascadia Mono with monospace fallbacks.
- Page title: 26 px, semibold.
- Section title: 16 px, semibold.
- Body: 14 px.
- Supporting text: 12–13 px, never below 12 px.

### Spacing and shape

- Base spacing unit: 4 px.
- Common gaps: 8, 12, 16, 24, and 32 px.
- Content max inset: 32 px.
- Control height: 38–42 px.
- Surface radius: 10 px; control radius: 7 px.
- Borders: 1 px. Shadows are avoided inside the desktop shell.

## Components

- **Navigation item:** icon-sized marker, visible label, selected rail, shortcut.
- **Surface:** titled grouping with optional supporting copy and action slot.
- **Page header:** eyebrow, title, concise explanation, optional primary action.
- **Notice:** status label, direct message, optional recovery action.
- **Empty state:** short explanation and one primary action.
- **Inspector row:** human label with optional monospace technical value.
- **Change tray:** pending count, validation state, and Review action.
- **Primary button:** one per decision group; accent fill.
- **Secondary button:** neutral raised surface.
- **Ghost button:** navigation or low-emphasis utility action.

## Interaction states

Every interactive component defines rest, hover, pressed, disabled, and keyboard
focus states. Selection and focus are distinct: selection uses a persistent
raised surface; focus uses a cyan outline.

Motion is limited to short page transitions and progress indication. The
application respects the operating system reduced-motion preference by keeping
all workflows understandable without animation.
