# VRIPT

## Annotation Steps
- Split scenes using `pyscenedetect`
- Generate caption for each scene
    - Use the provided prompt
    - Sample different #frames depending on duration

## Modifications in reproduction
- ❌Remove providing audio transcript
- ❌Remove providing video title (which was possibly included)
- ✅Change Model to gpt-4o (instead of gpt-4v)
- ✅Change to detail=auto(high) when calling gpt-4o (instead of low)