# Industrial Slate Design System

### 1. Overview & Creative North Star
**Creative North Star: "The Architectural Ledger"**

Industrial Slate is a design system rooted in technical precision and functional brutalism. It mimics the aesthetic of high-stakes documentation—classified briefings, architectural plans, and command-line interfaces—reimagined for a premium digital experience. It rejects the "bubbly" consumer web in favor of a utilitarian, high-contrast layout that prioritizes content over decoration.

The system breaks standard templates by using **Structured Asymmetry**. The sidebar acts as a heavy anchor, while the main content area utilizes wide margins and center-aligned columns to create a "document-first" reading rhythm. Depth is achieved not through shadows, but through the hard-edge layering of neutral tones.

### 2. Colors
The palette is a sophisticated range of architectural greys, punctuated by a high-visibility "Terminal Green" (Primary).

- **The "No-Line" Rule:** Sectioning is achieved through color blocks rather than borders where possible. For instance, the sidebar (`surface_container`) sits flush against the main body (`surface`), distinguished only by a subtle tonal shift. Use borders only when elements exist on the same background plane.
- **Surface Hierarchy & Nesting:**
    - **Surface Bright (#FFFFFF):** Used for AI-generated content or primary documents to ensure maximum readability.
    - **Surface Container High (#E2E2E4):** Used for user input or distinct UI blocks.
    - **Surface Container (#EAEAEB):** Used for structural navigation and sidebars.
- **Glass & Gradient:** Glassmorphism is used sparingly for headers (`background/90` with backdrop-blur) to maintain context while scrolling.
- **Signature Textures:** A subtle gradient (`to-transparent`) is used at the base of the viewport to fade content behind the input area, maintaining a "floating ledger" feel.

### 3. Typography
Industrial Slate utilizes a dual-font approach to balance readability with a technical aesthetic.

- **Display & UI:** `Inter` is the primary workhorse. It provides clarity at small sizes for labels and menus.
- **Data & Intelligence:** `IBM Plex Mono` is used for system responses, code blocks, and technical metadata, signaling the "machine" logic.

**Typography Scale (Calibrated):**
- **Headline (1rem / 16px):** Semibold, used for primary navigation and section headers.
- **Sub-headline (0.75rem / 12px):** Uppercase with 0.05em tracking for category labels (e.g., "THIS WEEK").
- **Body (15px):** The core reading size. A non-standard size that provides a "technical draft" feel, more compact than 16px but more legible than 14px.
- **Technical (0.85em):** Monospaced, used within code blocks and system status indicators.

### 4. Elevation & Depth
Depth in Industrial Slate is "flat." We move away from the Z-axis of Material Design toward a **Layered Plane** philosophy.

- **The Layering Principle:** Hierarchy is established by stacking. A `surface_bright` card sits on a `surface` background to denote importance.
- **Ambient Shadows:** Standard components use `shadow-none`. Only elevated floating utility bars (like message hover actions) use a `shadow-sm` (ultra-light, tight blur) to indicate they are temporary overlays.
- **The "Ghost Border":** Use `outline` (#D4D4D8) at 30-50% opacity for defining cards. It should feel like a faint pencil line on a blueprint.

### 5. Components
- **Buttons:** Low-radius (2px-4px). Primary buttons use the high-contrast Green/Black combo. Secondary buttons are tonal-grey to blend into the interface.
- **Input Fields:** Hard-edged rectangles. Focus states must use the Primary Green as a ring rather than a solid fill to maintain a "wireframe" aesthetic.
- **Message Bubbles:** Rectangular with minimal rounding (`rounded-md`). AI responses are bordered; user responses are tonal blocks.
- **Scrollbars:** Hidden or ultra-minimalist to prevent visual clutter in the "ledger" view.

### 6. Do's and Don'ts
**Do:**
- Use monospace for any data that feels "system-generated."
- Use "Surface Container" shifts to define different zones of the app.
- Keep corner radii very small (2px) to maintain the industrial feel.

**Don't:**
- Do not use large, soft, colorful shadows.
- Do not use rounded, pill-shaped buttons unless they are secondary floating actions.
- Avoid using the Primary Green for large background areas; it is a high-energy "signal" color only.