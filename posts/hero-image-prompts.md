# Hero image prompts — the flashing sign

Concept: a roadside fuel price board, with an oversized marquee arrow pointing
at the DIESEL row and announcing what it actually costs you.

Prices below are the real ones for the week of the post — gasoline $4.15,
diesel $5.96 — so the sign is accurate if a reader looks closely.

**Read the note at the bottom before generating.** Image models garble small
text and numbers, and this concept is almost entirely small text and numbers.

---

## A — Las Vegas marquee

> Photorealistic dusk photograph of an American roadside gas station price
> sign, low angle across an empty wet parking lot. The tall internally-lit
> price board lists four grades in white LED digits on black: REGULAR 4.15,
> PLUS 4.45, PREMIUM 4.79, DIESEL 5.96 — the DIESEL row rendered noticeably
> larger and brighter than the others. Bolted to the right edge of the board is
> an oversized 1950s Las Vegas–style marquee arrow in chrome and painted steel,
> outlined with hundreds of chasing incandescent bulbs in warm amber, angled so
> the arrow points directly at the DIESEL row. Deep blue twilight sky, warm bulb
> glow spilling across wet asphalt, faint lens flare. Cinematic grade in cream,
> deep teal-blue and burnt orange. Shot on 35mm, shallow depth of field, high
> detail. --ar 16:9

## B — Old-school diner

> Photorealistic dusk photograph of a roadside fuel price sign beside a 1950s
> googie-architecture diner. The price board lists REGULAR 4.15, PLUS 4.45,
> PREMIUM 4.79, DIESEL 5.96 in white LED digits on black. A vintage diner
> marquee — boomerang and starburst shapes, pink and turquoise neon tubing,
> a chrome arrow ringed with chasing bulbs — leans in from the right and points
> straight at the DIESEL row. Purple-blue dusk, neon reflecting on wet asphalt,
> a single parked semi truck blurred in the background. Warm nostalgic
> Americana palette, cinematic, 35mm, high detail. --ar 16:9

## C — Tighter, more graphic

> Close, straight-on photograph of the lower half of a gas station price board
> at night, cropped so DIESEL 5.96 fills the left two-thirds in glowing white
> LED digits. From the right, a chrome marquee arrow rimmed in chasing amber
> bulbs cuts diagonally across the frame and points at the diesel price. Black
> background, hard specular highlights on the chrome, deep shadow. High
> contrast, product-photography lighting, cinematic. --ar 16:9

---

## The text problem, and the fix

Every one of these asks a model to render exact digits (`5.96`, `44.4%`) and
words on a sign. Models are unreliable at this — expect `5.96` to come back as
`5.36` or `S.9G`, and expect `IMPACTS 44.4% OF YOUR EXPENSES!` to come back as
confident gibberish. Nano Banana Pro and Seedream 4 handle sign text better
than most; Midjourney and Flux will usually fail on it.

Two ways through:

**1. Generate the scene, composite the words.** Ask for the sign with blank or
illegible panels, then lay clean type over it. We already have an SVG pipeline
in the house palette, so the marquee line can be set in real Georgia at the
right size, in the exact same typography as the chart — and the number will
actually say 44.4%. This is the reliable route, and it keeps the figure
recomputed from the data rather than baked into an image.

To generate the plate, take prompt A or B and replace the price-board sentence
with:

> The price board's price panels are blank, unlit black rectangles with no
> digits or lettering. The marquee has an empty blank sign panel with no text.

**2. Roll the dice on a text-capable model,** then check every character.
A hero image with a typo in the price is worse than no hero image.

## Aspect ratios

- `hero` and `meta_image`: **1200×630** (`--ar 16:9` is close; crop to 1.91:1).
- If the hero also runs full-bleed at the top of the post, generate at
  **2400×1260** so it stays sharp on retina.

The sign image would replace `posts/cpi-diesel-card.png` as the hero. Worth
keeping the card for `meta_image` either way — link previews are small, and the
card is built to survive that.
