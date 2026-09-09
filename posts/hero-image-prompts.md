# Hero image prompts — the billboard

Concept: the view through a windshield while driving, and a roadside billboard
that reads **"Diesel prices impact 44.4% of your expenses."**

It plays off the ambulance-chaser line in the post — 444-4444, the number you
can't forget — so the billboard should look like *that* kind of billboard.
Cheap, loud, impossible to ignore, with **data4thepeople.com** running along
the bottom exactly where the lawyer's phone number would be.

The whole image hangs on one sentence rendering correctly. **Read "The text
problem" before generating.**

---

## A — Ambulance-chaser pastiche (the joke, full send)

> Photorealistic view through a car windshield from the driver's seat, driving
> on an American interstate. The dashboard and the top of the steering wheel
> are visible along the bottom edge, softly out of focus. Ahead and to the
> right, mounted on steel poles above the treeline, a large roadside billboard
> in the style of a cheap personal-injury-lawyer advertisement: saturated
> yellow background, enormous heavy condensed black and red lettering reading
> "DIESEL PRICES IMPACT 44.4% OF YOUR EXPENSES", and beneath it in smaller
> bold black capitals across the bottom of the board, "DATA4THEPEOPLE.COM".
> Slightly weathered vinyl, loud and unsubtle. Overcast flat daylight,
> telephone poles and guardrail
> rushing past with slight motion blur, the billboard itself sharp and in
> focus. Shot on 35mm, natural windshield reflections, high detail. --ar 16:9

## B — Straight and cinematic

> Photorealistic point-of-view shot through a windshield at golden hour on a
> rural American highway. Steering wheel and dashboard blurred along the bottom
> of the frame, rearview mirror at the top edge. A single large billboard
> stands to the right of the road against a wide sky, clean white background
> with bold black type reading "Diesel prices impact 44.4% of your expenses."
> and, smaller, along the bottom edge of the board, "data4thepeople.com".
> Warm low sun, long shadows across the asphalt, faint dust and lens flare, the
> road ahead empty. Cinematic color grade, shallow depth of field, shot on
> 35mm. --ar 16:9

## C — Tight crop, billboard dominant

> Photorealistic close view through a car windshield, angled up and to the
> right so a roadside billboard fills the upper two thirds of the frame. The
> billboard reads "DIESEL PRICES IMPACT 44.4% OF YOUR EXPENSES" in huge bold
> black letters on a plain yellow field, with "DATA4THEPEOPLE.COM" in smaller
> bold capitals along the bottom of the board. Bottom third shows the edge of the
> windshield, a sliver of dashboard and the rearview mirror, out of focus.
> Bright flat daylight, faint rain speckles on the glass, high contrast,
> documentary photography. --ar 16:9

## D — With the truck in frame

> Photorealistic view through a windshield on a multi-lane interstate. In the
> middle distance a diesel semi truck is pulling ahead in the right lane, its
> exhaust stack visible. Beyond it, a roadside billboard reads "DIESEL PRICES
> IMPACT 44.4% OF YOUR EXPENSES" in bold black type on yellow, with
> "DATA4THEPEOPLE.COM" in smaller bold capitals beneath it. Dashboard soft
> in the foreground. Grey overcast light, wet road spray, motion blur on the
> lane markings, billboard and truck both sharp. Documentary photojournalism,
> 35mm, high detail. --ar 16:9

The truck is worth having in frame — it puts the cause and the claim in the
same picture.

---

## The text problem

Everything above asks a model to spell a sentence, a URL, and `44.4%` exactly
right. That is the single least reliable thing image models do. Expect
`44.4%` to come back as `4.44%`, `44,4%` or `44.A%`, expect at least one word
of the sentence to be misspelled or duplicated, and expect the domain to come
back as `data4thepeple.com` or `data4thepeople.con`. The URL is the one piece
a reader might actually try to type, so it has to be right.

A hero image with the wrong number in it is worse than no hero image, and this
number is the entire post.

**The reliable route: generate a blank billboard, composite the type.** Take
any prompt above and replace the billboard sentence with:

> The billboard face is completely blank — a plain flat yellow rectangle with
> no text, no lettering, no logos, no numbers of any kind.

Then hand me the plate. I can lay the sentence and the URL on in the house
typography, matched to the billboard's perspective with an SVG transform, so
the number is correct, the domain is spelled right, the type is the same face
as the chart, and `44.4%` is recomputed from the data rather than typed in.
Same pipeline that renders the card.

**If you'd rather one-shot it:** Nano Banana Pro and Seedream 4 handle sign
text far better than Midjourney or Flux. Generate several, then read every
character of both the number and the domain before you use one.

---

## Sizes

- `hero` and `meta_image`: **1200×630**. `--ar 16:9` is close; crop to 1.91:1.
- Generate at **2400×1260** if the hero runs full-bleed, so it stays sharp on
  retina.

The billboard would take over `hero` from `posts/cpi-diesel-card.png`. Keep the
card on `meta_image` regardless — link previews render smallest of anything,
and the card is built to survive that while a photograph of distant text will
not.

---

## Earlier directions

A marquee-arrow version — a fuel price board with a Vegas or diner-style arrow
pointing at the diesel row — and a type-scaled version where the diesel price
is set 15× the gasoline price. Both are in git history at `3574e9f` if either
is worth revisiting. The type-scaled one is still buildable with
`render_static.py --sign linear`.
