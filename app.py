from flask import Flask
from youtubesearchpython import PlaylistsSearch

app = Flask("h")

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
        print("{},{},{},{}".format(result['channel']['name'], result['title'], result['videoCount'], result['link']))
    



@app.route('/reload')
def hello():
    return 'Hello, World!'