---
name: image-to-editable-canva
description: Generate or revise visual images, obtain user approval, convert the approved flat images into editable Canva designs with Magic Layers, inspect separated text and media elements, correct OCR errors in draft transactions, preview changes, and save only after explicit approval. Use when a user wants a generated poster, cover, social graphic, flyer, or similar image delivered as an editable Canva file.
---

# Image to Editable Canva

Turn an approved visual image into a checked, editable Canva design. Keep the workflow independent of visual style, palette, typography, and layout.

## Core rules

- Treat image design and Canva conversion as two separate stages.
- Do not invoke Magic Layers until the user explicitly approves the final image or asks to proceed.
- Preserve every approved raster image and any source-native file. Create new variants instead of overwriting approved work.
- Convert only the selected final variant. Do not spend Magic Layers uses on rejected drafts or exploratory versions.
- Treat OCR output as untrusted. Compare every extracted text element with the approved source copy.
- Keep Canva corrections in draft until the user sees the preview and explicitly approves saving.
- Do not claim a design is saved or finished before the commit operation succeeds.

## Workflow

### 1. Establish the deliverable

Determine:

- Number and type of images
- Required dimensions and aspect ratios
- Canonical copy and supplied assets
- Whether the user wants a new design, a visual revision, or both
- Whether Canva editability is required after approval

Make reasonable design assumptions when they do not change the requested outcome. Ask only when a missing choice would materially change the deliverable.

### 2. Generate or revise the images

Use the most appropriate production route:

- Use source-native SVG, HTML, Canvas, or layout code when deterministic editing is available.
- Use image generation or image editing when the work is raster-first or benefits from generative visuals.
- Preserve original assets and existing approved versions.
- Export a full-resolution PNG, JPEG, or WEBP for each candidate intended for Canva conversion.

Do not bind this Skill to any visual style. Follow the user's brief and references.

### 3. Inspect the visual output

Before showing a candidate, verify:

- Correct dimensions and aspect ratio
- No clipping, overlap, missing assets, or unintended empty areas
- Legible hierarchy at likely viewing size
- Correct names, dates, numbers, punctuation, and Chinese characters
- Consistent spacing, alignment, colors, and component treatment across a series
- Adequate text contrast

Render and inspect every final image. Fix visible problems before requesting approval.

### 4. Request image approval

Show the full preview and summarize only the material design decisions.

Ask the user to confirm that this exact image or image set should be converted to Canva. Mention the expected number of Magic Layers uses when known.

Stop here until the user clearly approves or asks to continue.

### 5. Convert with Canva Magic Layers

For each approved image:

1. Invoke Canva image-to-design with the final image file.
2. Use a descriptive, unique design title.
3. Treat each invocation as a new independent Canva design.
4. Record the returned design ID, thumbnail, edit URL, and view URL.
5. Show every returned thumbnail to the user when required by the Canva tool.

Do not substitute a flattened upload or HTML import when the user requires independently editable elements.

### 6. Audit the separated design

Start an editing transaction for each new design and retain its transaction ID and pages array.

Inspect:

- Every rich-text element against the canonical source copy
- Missing, merged, duplicated, or fragmented text boxes
- OCR substitutions, especially similar Chinese characters
- Numbers, Latin text, punctuation, spaces, and line breaks
- Whether meaningful text is editable rather than baked into an image
- Whether photos and major graphic regions appear as separate editable fills
- Obvious element displacement or text overflow introduced during separation

Always show the transaction thumbnail returned by Canva.

If a design needs no correction, cancel the inspection transaction cleanly. Do not leave it open.

### 7. Correct errors in draft mode

When corrections are required:

- Prefer `find_and_replace_text` for words or substrings.
- Use `replace_text` only when replacing an entire text element is appropriate.
- Batch corrections for the same design into one editing-operations call when possible.
- Reuse the exact transaction ID and pages array returned when the transaction started.
- Check whether the page is responsive before choosing an operation.
- Do not attempt unsupported Canva changes such as font-family replacement, background-gradient editing, shape restyling, or adding new text elements through the editing API.

If layout or styling requires substantial reconstruction, revise the source image and reconvert it after approval instead of forcing fragile Canva edits.

### 8. Preview and request save approval

After draft corrections:

1. Show the updated thumbnail.
2. List the exact corrections made.
3. State clearly that the changes are still drafts.
4. Ask whether to save them.

Do not commit without an explicit affirmative response.

If the user rejects the changes or changes direction, cancel every open transaction before returning to image design.

### 9. Commit and deliver

After approval:

1. Commit each editing transaction.
2. Confirm that every commit succeeded.
3. Return one clearly labeled Canva edit link per design.
4. State which files are editable and note any elements that Magic Layers could not separate.
5. Keep the approved raster and source-native files available as visual references and recovery assets.

## Multi-design handling

- Track each image, Canva design ID, transaction ID, and edit link separately.
- Never reuse a transaction ID across designs.
- Do not let a failure on one design obscure the status of the others.
- Report partial success precisely and retry only the failed design when appropriate.
- For a series, audit terminology consistently across all designs.

## Quality checklist

Before final delivery, confirm:

- The user approved the exact raster version that was converted.
- The Canva design came from Magic Layers or an equivalent element-separation workflow.
- Text elements were inspected against canonical copy.
- OCR errors were corrected or explicitly disclosed.
- Draft edits were committed only after approval.
- All open transactions were committed or cancelled.
- Every delivered edit link opens the intended design.
- The original raster and editable source were not overwritten.

## Failure handling

- If Magic Layers fails, retry only after confirming the source file is supported and readable.
- If separation quality is poor, simplify the source composition or increase contrast, obtain approval for the revised image, and reconvert.
- If a thumbnail or design link is unavailable, retrieve the design metadata before reporting completion.
- If authentication or quota blocks conversion, preserve the approved images and tell the user exactly what remains unfinished.
- Never upload a private local image to a public host merely to create an ingestible URL. Use the platform file-reference mechanism when available.
