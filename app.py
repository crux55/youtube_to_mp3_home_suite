import uuid

from flask import Flask, render_template
from youtubesearchpython import PlaylistsSearch
from flask import request
import os
import yt_dlp
import asyncio
from flask import jsonify
import json

app = Flask("h")
MANUAL_DOWNLOAD_FILE = r'manual_playlists.txt'
from flask_cors import CORS, cross_origin
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


def lidarr():
    import requests
    headers = {'Content-Type': 'application/json', "X-Api-Key":"8cc08967f4de4899b56299ee7950baeb"}
    response = requests.get('http://192.168.1.125:4547/api/v1/wanted/missing', headers=headers)
    all_links = []
    for record in response.json()['records']:
        album_name = record['title']
        artist_name = record['artist']['artistName']
        # print('{}, {}'.format(album_name, artist_name))
        all_links.append(Album(youtube_search(artist_name, album_name), album_name, artist_name, record['releases'][0]['trackCount']).toJSON())
    return all_links
    # album_id = response.json()['records'][0]['releases'][0]
    # artist_id = response.json()['records'][0]['artistId']
    # exit(0)

class Album():

    def __init__(self, playlist_result, title, artist_name, track_list_count):
        self.playlist_result = playlist_result
        self.title = title
        self.artist_name = artist_name
        self.track_list_count = track_list_count
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

class Playlist_Result():

    def __init__(self, channel_name, title, video_count, link):
        self.channel_name = channel_name
        self.title = title
        self.video_count = video_count
        self.link = link

def youtube_search(artist_name, album_name):
    frame = []
    videosSearch = PlaylistsSearch("{} {}".format(artist_name, album_name), limit = 10)
    for result in videosSearch.result()['result']:
        frame.append(Playlist_Result(result['channel']['name'], result['title'], result['videoCount'], result['link']))
    return frame

def check_or_make_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
    
async def call_album_puller():
    urls = open(MANUAL_DOWNLOAD_FILE, 'r').readlines()
    extension = ".mp3"
    tmp_ops = ydl_opts ={
        'no-overwrites': 'True',
        'ignoreerrors': 'True'
    }
    tmp_ops['format'] = "bestaudio/best"
    for url in urls:
        folder_for_download = '/mnt/UBERVAULT/Music/unimported/' + str(uuid.uuid4())
        check_or_make_dir(folder_for_download)
        file_path_and_regex = folder_for_download + '/%(title)s' + extension
        tmp_ops['outtmpl'] = file_path_and_regex
        with yt_dlp.YoutubeDL(tmp_ops) as ydl:
            ydl.download(url)


@app.route('/get-albums')
@cross_origin()
def generate():
    albums = lidarr()
    print(json.dumps(albums))
    return json.dumps(albums)

@app.route('/send', methods=['POST'])
def send():
    all_links = []
    for key in request.form.keys():
        all_links.append(request.form[key])
        # don't forget metadata'
    with open(MANUAL_DOWNLOAD_FILE, 'w') as fp:
        fp.write('\n'.join(all_links))
    asyncio.run(call_album_puller())
    return request.form
