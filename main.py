import os
import yaml
import yt_dlp
import json
from json import JSONDecodeError
from pathlib import Path
import time
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MEDIA_ROOT = os.environ.get('MEDIA_ROOT', '/mnt/UBERVAULT').rstrip('/\\')
# Windows drive roots like "Y:" need a separator to resolve as absolute paths.
if os.name == 'nt' and len(MEDIA_ROOT) == 2 and MEDIA_ROOT[1] == ':':
    MEDIA_ROOT = MEDIA_ROOT + os.sep


def normalize_config_path(path_value):
    """Map playlists.yaml's /mnt/UBERVAULT paths to MEDIA_ROOT for cross-platform runs."""
    normalized = str(path_value).replace('\\', '/')
    if normalized.startswith('/mnt/UBERVAULT'):
        suffix = normalized[len('/mnt/UBERVAULT'):].lstrip('/\\')
        return os.path.normpath(os.path.join(MEDIA_ROOT, suffix))
    return os.path.normpath(path_value)

ydl_opts = {
    'nooverwrites': True,
    'ignoreerrors': True,
    'extract_flat': False,
    'writethumbnail': False,
    'writeinfojson': False,
    'writedescription': False,
    'writesubtitles': False,
    'writeautomaticsub': False,
    'retries': 10,
    'fragment_retries': 10,
    'skip_unavailable_fragments': True,
    'extractor_retries': 3,
    'http_chunk_size': 10485760,  # 10MB chunks
    # 'web' keeps full-quality DASH formats for video playlists; 'android' is
    # dropped since its https formats now require a GVS PO token we don't
    # provide and it was only generating warnings. 'mweb'/'tv' are fallbacks
    # that still work unauthenticated when 'web' formats get SABR-throttled.
    'extractor_args': {'youtube': {'player_client': ['web', 'mweb', 'tv']}},
    }

_cookie_file = os.environ.get('YOUTUBE_COOKIES_FILE', '')
if _cookie_file and os.path.exists(_cookie_file):
    ydl_opts['cookiefile'] = _cookie_file


def check_or_make_dir(dir):
    if not os.path.exists(dir):
        try:
            os.makedirs(dir, exist_ok=True)
        except PermissionError:
            print(f"Warning: Cannot create directory {dir} - permission denied. Using current directory.")
            return False
    return True


def slugify_folder_name(name):
    """Create a filesystem-friendly folder name from a playlist label."""
    if not name:
        return "playlist"
    cleaned = re.sub(r"[^\w\-. ]+", "", str(name)).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "playlist"


def build_folder_for_download(playlist):
    """Resolve target folder from either explicit path or playlist root + name."""
    if playlist.get('playlist_root'):
        folder_name = playlist.get('folder_name') or playlist.get('name') or "playlist"
        return os.path.join(normalize_config_path(playlist['playlist_root']), slugify_folder_name(folder_name))

    if playlist.get('path'):
        return normalize_config_path('/'.join(playlist['path']))

    raise ValueError(
        f"Playlist '{playlist.get('name', 'unknown')}' needs either 'path' or 'playlist_root'"
    )


def write_playlist_m3u(folder_for_download, m3u_root, m3u_name=None):
    """Generate an M3U file that references downloaded audio files using relative paths."""
    audio_exts = {'.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.wav'}
    download_folder = Path(folder_for_download)
    root_folder = Path(m3u_root)

    if not download_folder.exists():
        logger.warning(f"Cannot create M3U. Download folder does not exist: {download_folder}")
        return

    check_or_make_dir(str(root_folder))

    tracks = sorted(
        [p for p in download_folder.iterdir() if p.is_file() and p.suffix.lower() in audio_exts],
        key=lambda p: p.name.lower()
    )

    if not tracks:
        logger.info(f"No audio tracks found for M3U generation in: {download_folder}")
        return

    playlist_filename = slugify_folder_name(m3u_name or download_folder.name) + '.m3u'
    m3u_path = root_folder / playlist_filename

    lines = ['#EXTM3U']
    for track in tracks:
        rel_path = os.path.relpath(str(track), str(root_folder)).replace('\\', '/')
        lines.append(rel_path)

    m3u_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    logger.info(f"Created/updated M3U file: {m3u_path}")


def expand_playlist_variants(playlist):
    """Expand a playlist entry into multiple concrete playlist configs if requested."""
    selected = playlist.get('playlist_selection')
    if not selected:
        return [playlist]

    expanded = []
    for idx, item in enumerate(selected):
        if not item or not item.get('url'):
            continue

        merged = dict(playlist)
        merged['url'] = item['url']

        item_name = item.get('name') or f"selection_{idx + 1}"
        merged['name'] = item_name
        merged['folder_name'] = item.get('folder_name', item_name)
        merged['m3u_name'] = item.get('m3u_name', item_name)
        expanded.append(merged)

    return expanded

def download_with_retry(ydl, urls, max_retries=3):
    """Download with retry logic and different strategies for signature extraction issues"""
    for attempt in range(max_retries):
        try:
            if isinstance(urls, str):
                urls = [urls]

            # With ignoreerrors enabled, a bad entry inside a playlist (e.g. a
            # DRM-protected track) no longer raises here - it's skipped and
            # logged by yt-dlp itself, and retcode comes back non-zero.
            retcode = ydl.download(urls)
            if retcode:
                logger.warning("Some entries were skipped due to errors (see above); continuing.")
            return True

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"Download attempt {attempt + 1} failed: {error_msg}")

            # Unrecoverable errors — no point retrying
            unrecoverable = [
                "copyright grounds",
                "Video unavailable",
                "This video has been removed",
                "account associated with this video has been terminated",
                "This video is private",
                "members-only",
                "Requested format is not available",
            ]
            if any(msg in error_msg for msg in unrecoverable):
                logger.warning("Unrecoverable error, skipping without retry.")
                return False

            if "Signature extraction failed" in error_msg and attempt < max_retries - 1:
                logger.info(f"Signature extraction failed, waiting 10 seconds before retry {attempt + 2}...")
                time.sleep(10)
                
                # Try to clear cache and update extractors
                try:
                    ydl.cache.remove()
                except:
                    pass
                    
                continue
            elif attempt < max_retries - 1:
                logger.info(f"Waiting 5 seconds before retry {attempt + 2}...")
                time.sleep(5)
                continue
            else:
                logger.error(f"All {max_retries} download attempts failed")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            else:
                return False
    
    return False
        

def read_datas(file):
    trading_info_file = Path(file)
    if not os.path.exists(trading_info_file):
        trading_info_file.touch(exist_ok=False)
        return {}
    # trading_info_file.touch(exist_ok=False)
    with open(trading_info_file, 'r') as file:
        try:
            content = json.load(file)
        except JSONDecodeError:
            return {}
        file.close()
        return content

def main():
    run_playlist_downloads()

def run_playlist_downloads():
    """Run the standard playlist downloads from playlists.yaml"""
    with open("playlists.yaml", "r") as stream:
        try:
            playlist_yaml = yaml.safe_load(stream)
            for playlist in playlist_yaml['playlists']:
                for playlist_item in expand_playlist_variants(playlist):
                    folder_for_download = build_folder_for_download(playlist_item)
                    check_or_make_dir(folder_for_download)
                    already_downloaded = read_datas(folder_for_download + '/downloaded.txt')

                    # Resolve format once so we don't mutate playlist config dicts.
                    resolved_format = str(playlist_item.get('format', '')).strip()
                    original_format_value = resolved_format.lower()
                    is_audio_only = (
                        original_format_value == 'audio_only'
                        or ('bestaudio' in original_format_value and 'bestvideo' not in original_format_value)
                    )

                    # Set output template and options based on format type
                    if is_audio_only:
                        # Avoid hard failures on some YouTube Music items where strict
                        # bestaudio is unavailable by allowing a best fallback.
                        if original_format_value == 'bestaudio':
                            resolved_format = 'bestaudio/best'
                        file_path_and_regex = folder_for_download + '/%(title)s.%(ext)s'
                        tmp_ops = ydl_opts.copy()
                        tmp_ops['postprocessors'] = [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }]
                    else:
                        file_path_and_regex = folder_for_download + '/%(title)s.mp4'
                        tmp_ops = ydl_opts.copy()

                    tmp_ops['outtmpl'] = file_path_and_regex
                    tmp_ops['format'] = resolved_format
                    tmp_ops['download_archive'] = folder_for_download + '/downloaded.txt'
                    if 'max_downloads' in playlist_item:
                        tmp_ops['max_downloads'] = playlist_item['max_downloads']

                    print(f"Processing playlist: {playlist_item.get('name', 'Unknown')} with format: {resolved_format}")

                    with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                        try:
                            if isinstance(playlist_item['url'], str):
                                print(f"Downloading from URL: {playlist_item['url']}")
                                success = download_with_retry(ydl, playlist_item['url'])
                                if not success:
                                    logger.error(f"Failed to download playlist: {playlist_item['url']}")
                            else:
                                for url in playlist_item['url']:
                                    print(f"Downloading from URL: {url}")
                                    success = download_with_retry(ydl, url)
                                    if not success:
                                        logger.error(f"Failed to download playlist: {url}")

                        except yt_dlp.utils.MaxDownloadsReached as de:
                            print(f"Max downloads reached: {de}")
                        except Exception as e:
                            print(f"Unexpected error: {e}")
                            # Try to continue with other playlists
                            continue

                    if playlist_item.get('create_m3u'):
                        m3u_root = normalize_config_path(
                            playlist_item.get('m3u_root', playlist_item.get('playlist_root', folder_for_download))
                        )
                        write_playlist_m3u(
                            folder_for_download=folder_for_download,
                            m3u_root=m3u_root,
                            m3u_name=playlist_item.get('m3u_name', playlist_item.get('name'))
                        )
        except yaml.YAMLError as exc:
            print(exc)

if __name__ == "__main__":
    main()
