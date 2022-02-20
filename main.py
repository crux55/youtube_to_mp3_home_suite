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
    'ignore-errors': 'True'
    }


def check_or_make_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
        
def lidarr():
    import requests
    import json
    headers = {'Content-Type': 'application/json', "X-Api-Key":"8cc08967f4de4899b56299ee7950baeb"}
    response = requests.get('http://192.168.1.103:4547/api/v1/wanted/missing', headers=headers)
    for record in response.json()['records']:
        album_name = record['title']
        artist_name = record['artist']['artistName']
        print('{}, {}'.format(album_name, artist_name))
        youtube_search(artist_name, album_name)
    # album_id = response.json()['records'][0]['releases'][0]
    # artist_id = response.json()['records'][0]['artistId']
    # exit(0)


def youtube_search(artist_name, album_name):
    videosSearch = PlaylistsSearch("{} {}".format(artist_name, album_name), limit = 10)
    for result in videosSearch.result()['result']:
        print("{} ({}): {}".format(result['channel']['name'], result['videoCount'], result['link']))
    

# lidarr()
# exit(0)

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
            file_path_and_regex = folder_for_download + '/%(artist)s--.%(album)s--%(title)s'
            already_downloaded = read_datas(folder_for_download + '/downloaded.txt')
            
            check_or_make_dir(folder_for_download)
            
            #set mp3 or mp4 based on what will output
            #set artist name and album in output file name
            
            tmp_ops = ydl_opts
            tmp_ops['outtmpl'] = file_path_and_regex
            tmp_ops['format'] = playlist['format']
            tmp_ops['download_archive'] = folder_for_download + '/downloaded.txt'
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
    except yaml.YAMLError as exc:
        print(exc)