# -*- coding: utf-8 -*-
import hashlib
import json
import time
from abc import abstractmethod
from os.path import join, exists
from urllib import request
import pyrebase
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import vk
from vk.exceptions import VkAPIError

import classify_image
from common import make_sure_path_exists, OUTPUT_DIR

TIME_TO_SLEEP = 0.35
TEMP_DIR = ".tmp"
CACHE_DIR = ".cache"


class DataSink:
    @abstractmethod
    def on_mushroom(self, lat, lon, url):
        pass


class TextfileSink(DataSink):
    def __init__(self, filename=join(OUTPUT_DIR, "latlons.txt")):
        self.filename = filename

    def on_mushroom(self, lat, lon, url):
        res = "{} {} {}\n".format(lat, lon, url)
        with open(self.filename, "a") as f:
            f.write(res)


class FirebaseSink(DataSink):
    def __init__(self, login, password, service_account_json):
        config = {
            "apiKey": "AIzaSyCht0LhaaZP89ICldZNXNYgnww5J9iaa38", #
            "authDomain": "mushroomm-b7709.firebaseapp.com", #
            "databaseURL": "https://mushroomm-b7709-default-rtdb.firebaseio.com", # https:///
            "storageBucket": "mushroomm-b7709.appspot.com", #gs://
            "serviceAccount": service_account_json
        }
        self.firebase = pyrebase.initialize_app(config)
        auth = self.firebase.auth()
        # authenticate a user
        self.user = auth.sign_in_with_email_and_password(login, password)
        self.db = self.firebase.database()

    def on_mushroom(self, lat, lon, url, date):
        h = hashlib.md5(str.encode(url)).hexdigest()
        data = {"lat": lat, "lon": lon, "url": url, "date":date}
        self.db.child("mushrooms").child(h).set(data, self.user['idToken'])


class VkScrapper:
    def __init__(self, vkapi, data_sink: DataSink):
        self.vkapi = vkapi
        self.keywords = {'mushroom', 'bolete', 'fungus'}
        self.group_keywords = {'грибы', 'грибники', 'грибочки', 'лес', 'грибов'}
        self.user_albums_keywords = {'грибы', 'грибники', 'грибочки', 'дача', 'лес', 'тихая охота', 'mushrooms'}
        self.processed_file = join(CACHE_DIR, "processed.txt")
        make_sure_path_exists(TEMP_DIR)
        make_sure_path_exists(CACHE_DIR)
        make_sure_path_exists(OUTPUT_DIR)
        self.tagger = classify_image.ImageTagger('.models')

        self.processed_users = set()
        if exists(self.processed_file):
            with open(self.processed_file, "r") as f:
                self.processed = set([s.strip() for s in f])
        else:
            self.processed = set()

        self.data_sink = data_sink

    def get_locations_by_user_or_group(self, owner, photo_processor):
        albums = self._api_call(self.vkapi.photos.getAlbums, owner_id=owner)
        if not albums:
            return
        for album in range(len(albums['items'])):
            photos = self._api_call(self.vkapi.photos.get, owner_id=str(owner), album_id=str(albums['items'][album]['id']), extended=True)
            if not photos:
                continue

            try:
                print("Photos in album {}".format(albums['items'][album]['title']))
            except UnicodeEncodeError as e:
                print("error printing album title")

            # print(photos)
            for p in photos['items']:
                photo_processor(p)
            time.sleep(TIME_TO_SLEEP)

    def __process_group_photo(self, p):
        try:
            self.__process_photo(p)
            if p['user_id'] > 0 and p['user_id'] not in self.processed_users:  # user uploaded this photo, probably she has many mushroom photos
                self.processed_users.add(p['user_id'])
                print("processing user ", p['user_id'])
                self.get_locations_by_user_or_group(p['user_id'], self.__process_photo)
        except Exception as e:
            print(e)

    def __process_photo(self, p):
        if not ('long' in p and 'lat' in p):
            return

        # src_variants = ['src_xbig', 'src_big', 'src_xxxbig', 'src']
        src_variants = ['s', 'm', 'x', 'o', 'p', 'q', 'r', 'y']     # s size<75px; m size<130px; x size<604; o proportion 3:2 and size<130px;
                                                                    # p proportion 3:2 and size<200px; q proportion 3:2 and size<320px;
                                                                    # r proportion 3:2 and size<510px; y proportion 3:2 and size<807px
        for size in range(len(p['sizes'])):
            if str(p['sizes'][size]['type']) in src_variants:
                tags = self.classify_photo(p['sizes'][size]['url'])
                picture = p['sizes'][size]['url']
                break
            else:
                return
        print(f"Тэги - {tags}")
        if not tags:
            return

        if not self.keywords.isdisjoint(tags):
            print("photo with address {} seems to contain mushrooms and has geotag:"
                  " lat = {}, lon = {}".format(picture, p['lat'], p['long']))
            if  (54.880609<= p['lat'] <= 59.246973)  and ( 36.485492 <= p['long'] <= 47.142231):
                self.data_sink.on_mushroom(p['lat'], p['long'], picture, p['date'])
            else:
                print(f"Неподходят координаты Широта: {p['lat']} и Долгота {p['long']}")
        else:
            print(
                "photo with address {} has no mushrooms and has geotag: lat = {}, lon = {}".format(
                    picture, p['lat'],
                    p['long']))

    def __process_photo_news(self, p):
        if not ('coordinates' in p['geo']):
            return

            # src_variants = ['src_xbig', 'src_big', 'src_xxxbig', 'src']
        src_variants = ['s', 'm', 'x', 'o', 'p', 'q', 'r',
                        'y']  # s size<75px; m size<130px; x size<604; o proportion 3:2 and size<130px;
        # p proportion 3:2 and size<200px; q proportion 3:2 and size<320px;
        # r proportion 3:2 and size<510px; y proportion 3:2 and size<807px
        exitFlag = False
        tags =''
        for attach in range(len(p['attachments'])):
                photoess = p['attachments'][attach].get('photo')
                try:
                    if photoess['sizes']:
                        for size in range(len(photoess['sizes'])):
                            if str(photoess['sizes'][size]['type']) in src_variants:
                                tags = self.classify_photo(photoess['sizes'][size]['url'])
                                picture = p['attachments'][attach]['photo']['sizes'][size]['url']
                                exitFlag = True
                                break
                            else:
                                return
                        if (exitFlag):
                            break
                except:
                    continue

        print(f"Тэги - {tags}")
        if not tags:
            return

        geoPos = str(p['geo']['coordinates']).split()
        if not self.keywords.isdisjoint(tags):
            print("photo with address {} seems to contain mushrooms and has geotag:"
                  " lat = {}, lon = {}".format(picture, geoPos[0], geoPos[1]))

            self.data_sink.on_mushroom(geoPos[0], geoPos[1], picture, p['date'])
        else:
            print(
                "photo with address {} has no mushrooms and has geotag: lat = {}, lon = {}".format(
                    picture, geoPos[0],
                    geoPos[1]))

    def get_all_locations(self):
        self.get_locations_by_groups()
        # self.get_locations_by_groups_members()

    def get_locations_by_groups(self):
        self._process_groups(lambda group: self.get_locations_by_user_or_group(
            -group.get('id'), self.__process_group_photo))

    def _process_groups(self, group_processor):
        groups_count_per_kw = 10
        for kw in self.group_keywords:
            groups = self._api_call(self.vkapi.groups.search, q=kw, count=groups_count_per_kw, lang='ru')
            if not groups:
                print("Failed to retrieve groups for keyword {}".format(kw))
                return
            # for group in groups[1:]:
            del_items_groups = groups['items']
            for group in range(len(del_items_groups)):
                try:
                    # print("scanning group {} (id {})".format(group.get('name'), group.get('gid')))
                    print(f"scanning group {del_items_groups[group].get('name')} (id {del_items_groups[group]['id']})" )
                except UnicodeEncodeError as e:
                    print("error printing group title")

                try:
                    group_processor(del_items_groups[group])
                except Exception as e:
                    print("Got error: ", e)

    def get_locations_by_groups_members(self):
        self._process_groups(lambda group: self.get_locations_by_users_in_group(group.get('gid')))

    def get_locations_by_users_in_group(self, gid):
        members_per_request = 1000
        offset = 0
        result = self._api_call(self.vkapi.groups.getMembers, group_id=gid, offset=offset, count=members_per_request)
        while result['count'] > offset:
            result = self._api_call(self.vkapi.groups.getMembers, group_id=gid, offset=offset,
                                    count=members_per_request, fields=["photo_max"])
            offset += members_per_request

            for owner in result['users']:
                self.get_locations_by_user_or_group(owner["id"], self.__process_photo)
            print("Processed {} users".format(len(result['users'])))

    def classify_photo(self, url):
        h = hashlib.md5(str.encode(url)).hexdigest()
        if h in self.processed:
            return None

        image_path = join(TEMP_DIR, 'img.jpg')
        print(f"Путь файла {image_path}")
        with open(image_path, 'wb') as f:
            f.write(request.urlopen(url).read())

        print("Запись в просессед файл")
        with open(self.processed_file, "a") as f:
            f.write("{}\n".format(h))
        print("Закончилась запись в файлы")
        return self.tagger.run_inference_on_image(image_path)

    def close(self):
        self.tagger.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tagger.close()

    # news scraper

    def get_mushroom_from_newsfeed(self):
        posts_count = 10
        next_from = 0
        coordinates = {'1':'57.957837 39.815929', '2':'58.325317 39.847483', '3':'58.65531 39.124423', '4':'58.661024 40.618564', '5':'58.568543 42.945968', '6':'58.028759 43.356216', '7':'57.53087 44.595524', '8':'56.487069 44.73754', '9':'57.208012 40.787955', '10':'56.958759 40.450125', '11':'57.049997 38.519278', '12':'57.592816 38.763872','13':'57.044093 38.505694'}
        for kw in self.user_albums_keywords:
            for i in range(len(coordinates)):
                lat_place = coordinates[str(i+1)].split()[0]
                long_place = coordinates[str(i+1)].split()[1]
                posts = vkapi.newsfeed.search(q=kw, count=posts_count, start_from=next_from, latitude=lat_place,longitude=long_place)
                print(f'Итерация {i}')
                for i in range(len(posts['items'])):
                    attachments = posts['items'][i]
                    self.__process_photo_news(attachments)

    def _api_call(self, method, *args, **kwargs):
        for i in range(3):
            try:
                return method(*args, **kwargs)
            except VkAPIError as e:
                if e.code == 6:  # just too many requests
                    time.sleep(TIME_TO_SLEEP)
                else:
                    print("error {}".format(e.code))
                    return None
        return None

import vk_api

if __name__ == "__main__":
    private_data = json.load(open("private.txt"))

    if "vk_token" not in private_data:
        print("No tokens found!")
        exit(0)

    login = 0 # phone number from vk
    passwd = 0 # password from vk
    vk_session = vk_api.VkApi(login, passwd)
    vk_session.auth()
    vkapi = vk_session.get_api()

    # session = vk.Session(access_token=private_data["vk_token"])
    # vkapi = vk.API(session)

    #sink = TextfileSink()
    try:
        sink = FirebaseSink(private_data["firebase_login"],
                            private_data["firebase_password"], private_data["service_account_json"])
    except Exception as e:
        print("Error creating firebase sink. Using plain text.")
        sink = TextfileSink()
    scrapper = VkScrapper(vkapi, sink)
    variant_of_scraping = int(input("Enter the type of scraping(1 - newsfeed/2 - groups):  "))
    if variant_of_scraping == 1:
        scrapper.get_mushroom_from_newsfeed()
    elif variant_of_scraping == 2:
         scrapper.get_all_locations()
