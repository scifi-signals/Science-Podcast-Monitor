# update_site.py
# Updates the site manifest with all available podcast digests

import os
import json
import glob
import re
from datetime import datetime


def get_digest_info(filepath):
    """Extract info from a digest file."""
    filename = os.path.basename(filepath)

    # Extract date from filename (digest_YYYYMMDD_HHMM.html)
    match = re.search(r'digest_(\d{8})_(\d{4})\.html', filename)
    if not match:
        return None

    date_str = match.group(1)
    time_str = match.group(2)

    try:
        dt = datetime.strptime(date_str + time_str, '%Y%m%d%H%M')
        formatted_date = dt.strftime('%B %d, %Y')
    except Exception:
        formatted_date = date_str
        dt = None

    # Count episodes by looking for "episode" divs in the file
    episode_count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            episode_count = content.count('class="episode"')
    except Exception:
        pass

    mtime = os.path.getmtime(filepath)

    return {
        'file': filename,
        'date': formatted_date,
        'timestamp': dt.isoformat() if dt else date_str,
        'mtime': mtime,
        'episodes': episode_count
    }


def update_manifest():
    """Update the digest manifest file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    pattern = os.path.join(script_dir, 'digest_*.html')
    digest_files = glob.glob(pattern)

    digests = []
    for filepath in digest_files:
        info = get_digest_info(filepath)
        if info:
            digests.append(info)

    # Sort by file modification time (newest first)
    digests.sort(key=lambda x: x.get('mtime', 0), reverse=True)

    # Remove mtime from output
    for d in digests:
        d.pop('mtime', None)

    # Keep last 15 digests
    digests = digests[:15]

    manifest = {
        'updated': datetime.now().isoformat(),
        'digests': digests
    }

    manifest_path = os.path.join(script_dir, 'digest_manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"Updated manifest with {len(digests)} digests")
    for d in digests[:3]:
        print(f"  - {d['file']}: {d['date']} ({d['episodes']} episodes)")

    return manifest


def cleanup_old_digests(keep_count=15):
    """Remove old digest files beyond the keep count."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(script_dir, 'digest_*.html')
    digest_files = sorted(glob.glob(pattern), reverse=True)

    if len(digest_files) > keep_count:
        old_files = digest_files[keep_count:]
        for filepath in old_files:
            print(f"  Removing old digest: {os.path.basename(filepath)}")
            os.remove(filepath)
        print(f"Cleaned up {len(old_files)} old digest files")


if __name__ == '__main__':
    print("Updating site manifest...")
    update_manifest()
    print("\nCleaning up old digests...")
    cleanup_old_digests()
    print("\nDone!")
