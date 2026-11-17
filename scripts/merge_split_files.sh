#!/bin/bash
# One-off cleanup: merge leftover yt-dlp pieces (NAME.mp4.fNNN.<ext>) into NAME.mp4.
# Dry run by default; pass --apply to merge and delete the pieces.
# Usage: scripts/merge_split_files.sh [--apply] [root ...]   (default roots: Music and Video)
apply=0
if [ "${1:-}" = "--apply" ]; then apply=1; shift; fi
roots=("$@")
[ ${#roots[@]} -eq 0 ] && roots=(/mnt/UBERVAULT/Music /mnt/UBERVAULT/Video)

# Group pieces by their final name (everything before ".fNNN.ext").
find "${roots[@]}" -type f -regextype posix-extended -regex '.*\.f[0-9]+\.[a-z0-9]+' -print0 |
while IFS= read -r -d '' piece; do
    echo "${piece%.f[0-9]*}"
done | sort -u |
while IFS= read -r final; do
    mapfile -t pieces < <(find "$(dirname "$final")" -maxdepth 1 -type f -name "$(basename "$final").f[0-9]*")
    if [ -e "$final" ]; then
        echo "SKIP (final exists, leaving pieces alone): $final"; continue
    fi
    if [ ${#pieces[@]} -lt 2 ]; then
        echo "SKIP (only one piece, needs manual look): $final"; continue
    fi
    echo "MERGE ${#pieces[@]} pieces -> $final"
    [ $apply -eq 1 ] || continue
    inputs=(); for p in "${pieces[@]}"; do inputs+=(-i "$p"); done
    ffmpeg -nostdin -loglevel error "${inputs[@]}" -map 0 -map 1 -c copy -f mp4 "$final.part" \
        && mv "$final.part" "$final" && rm -- "${pieces[@]}"
done
