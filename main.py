from datetime import date
from youtubesearchpython import PlaylistsSearch
import os
import yaml
import yt_dlp
import json
from json import JSONDecodeError
from pathlib import Path
from ytmusicapi import YTMusic
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import requests

ydl_music_opts = {
    'no-overwrites': 'True',
    'ignoreerrors': 'True',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
        }],
}

ydl_opts ={
    'no-overwrites': 'True',
    'ignoreerrors': 'True',
    # 'listformats' : 'False'
    }


def check_or_make_dir(dir):
    if not os.path.exists(dir):
        try:
            os.makedirs(dir, exist_ok=True)
        except PermissionError:
            print(f"Warning: Cannot create directory {dir} - permission denied. Using current directory.")
            return False
    return True
        
def lidarr():
    """Fetch missing albums/tracks from Lidarr and download them"""
    headers = {'Content-Type': 'application/json', "X-Api-Key":"8cc08967f4de4899b56299ee7950baeb"}
    response = requests.get('http://192.168.1.125:4547/api/v1/wanted/missing', headers=headers)
    
    for record in response.json()['records']:
        album_name = record['title']
        artist_name = record['artist']['artistName']
        album_id = record.get('id')
        artist_id = record['artist'].get('id')
        release_date = record.get('releaseDate', '')
        year = release_date[:4] if release_date else ''
        
        print('\n=== Processing: {}, {} ==='.format(album_name, artist_name))
        
        # Check if this record has individual tracks (track-level missing items)
        if 'tracks' in record and record['tracks']:
            # Track-level download
            print(f"Found {len(record['tracks'])} missing track(s)")
            for track in record['tracks']:
                track_name = track.get('title', 'Unknown')
                track_number = track.get('trackNumber', 0)
                youtube_music_download_track(
                    artist_name=artist_name,
                    album_name=album_name,
                    track_name=track_name,
                    track_number=track_number,
                    year=year
                )
        else:
            # Album-level download (full album)
            youtube_music_download(artist_name, album_name, year)


def youtube_search(artist_name, album_name):
    videosSearch = PlaylistsSearch("{} {}".format(artist_name, album_name), limit = 10)
    for result in videosSearch.result()['result']:
        print("{} ({}): {}".format(result['channel']['name'], result['videoCount'], result['link']))

def youtube_music_download(artist_name, album_name, year=''):
    """Search YouTube Music for album and download it"""
    ytmusic = YTMusic()
      # Search for the album on YouTube Music
    search_query = f"{artist_name} {album_name}"
    search_results = ytmusic.search(search_query, filter='albums', limit=5)
    
    if not search_results:
        print(f"No albums found for: {search_query}")
        return
    
    # Display results and use the first match
    print(f"Found {len(search_results)} album(s):")
    for idx, album in enumerate(search_results[:3]):
        album_title = album.get('title', 'Unknown')
        album_artist = album['artists'][0]['name'] if album.get('artists') else 'Unknown'
        year = album.get('year', 'N/A')
        print(f"  {idx+1}. {album_artist} - {album_title} ({year})")
    
    # Use the first result (best match)
    best_match = search_results[0]
    browse_id = best_match['browseId']
    
    # Get album details including tracks
    album_details = ytmusic.get_album(browse_id)
    
    album_title = album_details.get('title', album_name)
    album_artist = album_details['artists'][0]['name'] if album_details.get('artists') else artist_name
    # Use passed-in year if provided, otherwise get from album details
    final_year = year or album_details.get('year', '')
    
    print(f"\nDownloading: {album_artist} - {album_title}")
    print(f"Tracks: {len(album_details.get('tracks', []))}")
    
    # Create directory structure
    base_dir = '/mnt/UBERVAULT/Music/Albums'
    artist_dir = os.path.join(base_dir, sanitize_filename(album_artist))
    album_dir = os.path.join(artist_dir, sanitize_filename(album_title))
    
    if not check_or_make_dir(album_dir):
        print(f"Failed to create directory: {album_dir}")
        return
    
    print(f"Saving to: {album_dir}")
    
    # Configure yt-dlp for this download
    cookie_file = os.environ.get('YOUTUBE_COOKIES_FILE', '')
    download_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(album_dir, '%(title)s.%(ext)s'),
        'download_archive': os.path.join(album_dir, 'downloaded.txt'),
        'ignoreerrors': True,
        'no_warnings': False,
        'cookiefile': cookie_file if cookie_file and os.path.exists(cookie_file) else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'mweb'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    # Download each track
    with yt_dlp.YoutubeDL(download_opts) as ydl:
        for idx, track in enumerate(album_details.get('tracks', []), 1):
            video_id = track.get('videoId')
            if video_id:
                track_title = track.get('title', 'Unknown')
                print(f"  Downloading: {track_title}")
                try:
                    info = ydl.extract_info(f'https://youtube.com/watch?v={video_id}', download=True)
                    
                    if info is None:
                        print(f"    Failed to extract info for {track_title}, skipping...")
                        continue
                    
                    mp3_file = ydl.prepare_filename(info).replace(info['ext'], 'mp3')
                    
                    # Apply metadata to downloaded file
                    if os.path.exists(mp3_file):
                        apply_metadata(
                            mp3_file,
                            artist=album_artist,
                            album=album_title,
                            title=track_title,
                            track_number=idx,
                            year=final_year
                        )
                except Exception as e:
                    print(f"    Error downloading {track_title}: {e}")


def youtube_music_download_track(artist_name, album_name, track_name, track_number, year):
    """Search YouTube Music for a specific track and download it"""
    ytmusic = YTMusic()
    
    # Search for the specific track
    search_query = f"{artist_name} {track_name}"
    search_results = ytmusic.search(search_query, filter='songs', limit=5)
    
    if not search_results:
        print(f"  No tracks found for: {search_query}")
        return
    
    # Use the first result (best match)
    best_match = search_results[0]
    video_id = best_match.get('videoId')
    
    if not video_id:
        print(f"  Could not find video ID for: {track_name}")
        return
    
    track_title = best_match.get('title', track_name)
    matched_artist = best_match['artists'][0]['name'] if best_match.get('artists') else artist_name
    
    print(f"  Found: {matched_artist} - {track_title}")
    
    # Create directory structure
    base_dir = '/mnt/UBERVAULT/Music/Albums'
    artist_dir = os.path.join(base_dir, sanitize_filename(artist_name))
    album_dir = os.path.join(artist_dir, sanitize_filename(album_name))
    
    if not check_or_make_dir(album_dir):
        print(f"  Failed to create directory: {album_dir}")
        return
    
    # Configure yt-dlp for this download
    download_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(album_dir, '%(title)s.%(ext)s'),
        'download_archive': os.path.join(album_dir, 'downloaded.txt'),
        'ignoreerrors': True,
        'no_warnings': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    # Download the track
    with yt_dlp.YoutubeDL(download_opts) as ydl:
        try:
            print(f"  Downloading: {track_title}")
            info = ydl.extract_info(f'https://music.youtube.com/watch?v={video_id}', download=True)
            mp3_file = ydl.prepare_filename(info).replace(info['ext'], 'mp3')
            
            # Apply metadata to downloaded file
            if os.path.exists(mp3_file):
                apply_metadata(
                    mp3_file,
                    artist=artist_name,
                    album=album_name,
                    title=track_title,
                    track_number=track_number,
                    year=year
                )
                print(f"  ✓ Downloaded and tagged: {track_title}")
        except Exception as e:
            print(f"  Error downloading {track_title}: {e}")


def apply_metadata(mp3_file, artist, album, title, track_number, year):
    """Apply ID3 metadata to MP3 file"""
    try:
        # Use EasyID3 for simple metadata
        audio = EasyID3(mp3_file)
        audio['artist'] = artist
        audio['album'] = album
        audio['title'] = title
        audio['date'] = year if year else ''
        audio['tracknumber'] = str(track_number)
        audio.save()
        print(f"    Metadata applied: {artist} - {title}")
    except Exception as e:
        print(f"    Warning: Could not apply metadata to {mp3_file}: {e}")

def sanitize_filename(filename):
    """Remove invalid characters from filenames"""
    import re
    # Replace invalid characters with underscore
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    return filename
    

lidarr()
exit()
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

with open("playlists.yaml", "r") as stream:
    try:
        playlist_yaml = yaml.safe_load(stream)
        for playlist in playlist_yaml['playlists']:
            extension = ".mp4"
            tmp_ops = ydl_opts
            if 'audio_only' in playlist:
                extension = ".mp3"
                tmp_ops = ydl_music_opts
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
            if 'reverse' in playlist:
                tmp_ops['playlistreverse'] = True
            if 'datebefore' in playlist:
                tmp_ops['datebefore'] = DateRange(end=str(playlist['datebefore']))
            if 'dateafter' in playlist:
                tmp_ops['daterange'] = DateRange(start=str(playlist['dateafter']))
            if 'playlist_items' in playlist:
                tmp_ops['playlist_items'] = playlist['playlist_items']
            with yt_dlp.YoutubeDL(tmp_ops) as ydl:
                    try:
                        if isinstance(playlist['url'], str):
                            ydl.download([playlist['url']])
                        else:
                            for url in playlist['url']:
                                print(url)
                                ydl.download(url)
                    except yt_dlp.utils.DownloadError as de:
                        print(de)
                    except yt_dlp.utils.MaxDownloadsReached as de:
                        print(de)
    except yaml.YAMLError as exc:
        print(exc)
