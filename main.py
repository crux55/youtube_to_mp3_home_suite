from youtubesearchpython import PlaylistsSearch
import os
import yaml
import yt_dlp
import json
from json import JSONDecodeError
from pathlib import Path

ydl_music_opts = {
    'format': 'bestaudio/best',
    'download_archive': 'downloaded_songs.txt',
    'outtmpl': '%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
        }],
}

ydl_opts ={
    'no-overwrites': 'True',
    'ignore_errors': 'True',
    # 'listformats' : 'False'
    }


def check_or_make_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
        
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
            folder_for_download = '/'.join(playlist['path'])
            file_path_and_regex = folder_for_download + '/%(title)s.mp4'
            check_or_make_dir(folder_for_download)
            already_downloaded = read_datas(folder_for_download + '/downloaded.txt')
            
            
            #set mp3 or mp4 based on what will output
            #set artist name and album in output file name
            
            tmp_ops = ydl_opts
            tmp_ops['outtmpl'] = file_path_and_regex
            tmp_ops['format'] = playlist['format']
            tmp_ops['download_archive'] = folder_for_download + '/downloaded.txt'
            if 'max_downloads' in playlist:
                tmp_ops['max_downloads'] = playlist['max_downloads']
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