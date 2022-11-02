from flask import Flask, render_template
from youtubesearchpython import PlaylistsSearch
from flask import request

app = Flask("h")

def lidarr():
    import requests
    import json
    headers = {'Content-Type': 'application/json', "X-Api-Key":"8cc08967f4de4899b56299ee7950baeb"}
    response = requests.get('http://192.168.1.30:4547/api/v1/wanted/missing', headers=headers)
    all_links = []
    for record in response.json()['records']:
        album_name = record['title']
        artist_name = record['artist']['artistName']
        # print('{}, {}'.format(album_name, artist_name))
        all_links.append(Album(youtube_search(artist_name, album_name), album_name, artist_name, record['releases'][0]['trackCount']))
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
    



@app.route('/reload')
def generate():
    albums = lidarr()
    return render_template('index.html', albums=albums)

@app.route('/send', methods=['POST'])
def send():
    all_links = []
    for key in request.form.keys():
        all_links.append(request.form[key])
        # don't forget metadata'
    with open(r'manual_playlists.txt', 'w') as fp:
        fp.write('\n'.join(all_links))
    return request.form
