# Character registry (rules r19 + r26)

One folder per named character: `<id>/sheet.json` (look, colours, signature costume, design source, ONE Fish voice),
`<id>/sheet.png` (turnaround: `node film/scripts/sheet.mjs <id>`). The drawing lives in `film/src/characters/<id>.ts`
and must use exactly the sheet's colours (checked by `tc still --chars` and the film tests).
A character is created once, checked (`python -m tc characters check <id>`) and then locked: every video draws the
same person in brand-new scenes. Generic people (soldiers, crowds, servants) are not registered.
Older 3D design notes for the same people are in `library/cast/` (design sources only; the 3D data is unused).
