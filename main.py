import os
import yaml
import yt_dlp
import json
from json import JSONDecodeError
from pathlib import Path
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ydl_opts = {
    'no_overwrites': True,
    'ignore_errors': True,
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
    'extractor_args': {'youtube': {'player_client': ['web', 'android', 'mweb']}},
    }


def check_or_make_dir(dir):
    if not os.path.exists(dir):
        try:
            os.makedirs(dir, exist_ok=True)
        except PermissionError:
            print(f"Warning: Cannot create directory {dir} - permission denied. Using current directory.")
            return False
    return True

def download_with_retry(ydl, urls, max_retries=3):
    """Download with retry logic and different strategies for signature extraction issues"""
    for attempt in range(max_retries):
        try:
            if isinstance(urls, str):
                urls = [urls]
            
            ydl.download(urls)
            return True
            
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"Download attempt {attempt + 1} failed: {error_msg}")
            
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
                folder_for_download = '/'.join(playlist['path'])
                check_or_make_dir(folder_for_download)
                already_downloaded = read_datas(folder_for_download + '/downloaded.txt')
                
                # Check if this is an audio-only format
                is_audio_only = playlist['format'] in ['bestaudio/best', 'bestaudio', 'audio_only']
                
                # Set output template and options based on format type
                if is_audio_only:
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
                tmp_ops['format'] = playlist['format']
                tmp_ops['download_archive'] = folder_for_download + '/downloaded.txt'
                if 'max_downloads' in playlist:
                    tmp_ops['max_downloads'] = playlist['max_downloads']
                
                print(f"Processing playlist: {playlist.get('name', 'Unknown')} with format: {playlist['format']}")
                
                with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                    try:
                        if isinstance(playlist['url'], str):
                            print(f"Downloading from URL: {playlist['url']}")
                            success = download_with_retry(ydl, playlist['url'])
                            if not success:
                                logger.error(f"Failed to download playlist: {playlist['url']}")
                        else:
                            for url in playlist['url']:
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
        except yaml.YAMLError as exc:
            print(exc)

if __name__ == "__main__":
    main()
