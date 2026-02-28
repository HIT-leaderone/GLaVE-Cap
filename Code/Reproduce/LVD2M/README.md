# LVD-2M

## Annotation Steps
- For each 30 seconds, sample 6 frames and get its caption in one inference
- Refine each caption
- Summary those captions into one

## Modifications in reproduction
- ⚠️Originally designed for videos with no scene cut, but we don't guarantee this
- ✅Six images are given separately, in high res, instead of put in a 2x3 grid
- ✅Use gpt-4o instead of LLaVA-v1.6-34B
- ✅Use gpt-4o instead of Claude3-Haiku
