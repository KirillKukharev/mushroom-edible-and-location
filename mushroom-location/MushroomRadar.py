import requests
import json
import pyrebase


import ssl

ssl._create_default_https_context = ssl._create_unverified_context

firebase_config = {
    "apiKey": "AIzaSyCht0LhaaZP89ICldZNXNYgnww5J9iaa38",  #
    "authDomain": "mushroomm-b7709.firebaseapp.com",  #
    "databaseURL": "https://mushroomm-b7709-default-rtdb.firebaseio.com",  # https:///
    "storageBucket": "mushroomm-b7709.appspot.com",  # gs://
    "serviceAccount": 'mushroomm-b7709-firebase-adminsdk-3z1dn-20eff067a0.json'
}

firebase = pyrebase.initialize_app(firebase_config)

db = firebase.database()

coordinates = {'1':'57.957837 39.815929', '2':'58.325317 39.847483', '3':'58.65531 39.124423', '4':'58.661024 40.618564', '5':'58.568543 42.945968', '6':'58.028759 43.356216', '7':'57.53087 44.595524', '8':'56.487069 44.73754', '9':'57.208012 40.787955', '10':'56.958759 40.450125', '11':'57.049997 38.519278', '12':'57.592816 38.763872','13':'57.044093 38.505694'}
# coordinates = {'1':'57.957837 39.815929'}

## -*- coding: utf-8 -*-
import os, time, sys, csv, urllib, itertools, math, subprocess
import urllib.request


class Station:
    def __init__(self, name, province, max_temp, min_temp, avg_temp, gust_wind, max_wind, prec_24h, prec_0_6, prec_6_12,
                 prec_12_18, prec_18_24, soil_temp, soil_prec, days_ago):
        attribute_list = [name, province, max_temp, min_temp, avg_temp, gust_wind, max_wind, prec_24h, prec_0_6,
                          prec_6_12, prec_12_18, prec_18_24, soil_temp, soil_prec]
        for attribute in attribute_list:
            if attribute == '':
                raise ValueError("An attribute is absent from %s" % (attribute, self.__class__.__name__))

        self.name = name
        self.province = province
        self.max_temp = max_temp
        self.min_temp = min_temp
        self.avg_temp = avg_temp
        self.gust_wind = gust_wind
        self.max_wind = max_wind
        self.prec_24h = prec_24h
        self.prec_0_6 = prec_0_6
        self.prec_6_12 = prec_6_12
        self.prec_12_18 = prec_12_18
        self.prec_18_24 = prec_18_24
        self.soil_temp = soil_temp
        self.soil_prec = soil_prec
        self.days_ago = days_ago

    def gen_score(self):
        if float(self.avg_temp) == 15:  # ideal temp of 15C, more points for staying close
            score = 100
        elif float(self.avg_temp) > 32:
            score = -900
        elif float(self.avg_temp) < 4:
            score = -900
        else:
            score = 100 - (abs(float(self.avg_temp) - 15)) * 5

            # points for quantity of rain + extra for constant rain
        if float(self.prec_24h) >= 2:
            score += 100
        elif 1.5 < float(self.prec_24h) < 2:
            score += 150
        elif 1.0 < float(self.prec_24h) < 1.5:
            score += 80
        else:
            score += 40

        if float(self.prec_0_6) > 0.5:
            score += 50
        if float(self.prec_6_12) > 0.5:
            score += 30
        if float(self.prec_12_18) > 0.5:
            score += 40
        if float(self.prec_18_24) > 0.5:
            score += 30

        if float(self.max_wind) > 15:  # wind over 15kph will dry out mushrooms, subtract points
            score += -float(self.max_wind) / 2

        if float(self.min_temp) < 5:  # penalties for extreme weather
            score += -800
        if float(self.max_temp) > 25:
            score += -150
        if float(self.gust_wind) > 40:
            score += -10

        if 20 < float(self.soil_temp) < 13:
            score += 300
        elif float(self.soil_temp) < 3:
            score += -300
        elif float(self.soil_temp) > 20:
            score += -100
        else:
            score += 0

        if 0.3 < float(self.soil_prec) < 0.7:
            score += 220
        elif 0.1 < float(self.soil_prec) < 0.3:
            score += -100
        elif 0.7 < float(self.soil_prec) < 1.0:
            score += 100
        else:
            score += 0

        if 0 < float(self.days_ago) < 1:
            # score = score / 870
            score = score / 670
        else:
            # score = (score * 3) / 8700
            score = (score * 4) / 6700
        # score=score*(self.days_ago/3)
        # print(f'сколько дней {self.days_ago} скор {score}')
        return score

def parse_data(arr_with_params,days_in_future,object_list):
		try:
			object_list.append(Station(arr_with_params[0],arr_with_params[1],arr_with_params[2],arr_with_params[3],arr_with_params[4],arr_with_params[5],arr_with_params[6],arr_with_params[7],arr_with_params[8],arr_with_params[9],arr_with_params[10],arr_with_params[11],arr_with_params[12],arr_with_params[13],days_in_future))
		except:
			pass


key = "63829f23-7ffc-4132-9b3f-80cd7c620a36"
json_to_save = []
list_of_stations=[]
for loc in coordinates:
  coords = coordinates[loc].split()
  lat = coords[0]
  lon = coords[1]
  rec = requests.get("https://api.weather.yandex.ru/v2/forecast?",
                 params={'lat': lat, 'lon': lon, 'lang': 'ru_UA', 'extra': 'true', 'hours': 'true'}, headers={'X-Yandex-API-Key': key,})
  json_to_save.append(rec.text)
  time.sleep(5)
  try:
    response_dict = json.loads(rec.text)
    # print(response_dict['geo_object']['locality']['name'])
    name_of_loc = response_dict['geo_object']['locality']['name']
    arr=[]
    for days in range(7):
      arr.append(response_dict['forecasts'][days])
    for day in range(len(arr)-4): # получение прогнозов на +3 дня вперед и -3 дня назад
      max_temp_pr = arr[day]['parts']['day']['temp_max']
      min_temp_pr = arr[day]['parts']['day']['temp_min']
      avg_temp_pr = arr[day]['parts']['day']['temp_avg']
      wind_gust_pr = arr[day]['parts']['day_short']['wind_gust']
      wind_speed_temp = arr[day]['parts']['day_short']['wind_speed']
      precipation_pred_24 = (arr[day]['parts']['day_short']['prec_mm'] + arr[day]['parts']['night_short']['prec_mm']) / 2
      precipation_pred_0_6 = round(sum([arr[day]['hours'][hour]['prec_mm'] for hour in range(6)])/6, 2)
      precipation_pred_6_12 = round(sum([arr[day]['hours'][hour]['prec_mm'] for hour in range(6,12)])/6,2)
      precipation_pred_12_18 = round(sum([arr[day]['hours'][hour]['prec_mm'] for hour in range(12,18)])/6, 2)
      precipation_pred_18_24 = round(sum([arr[day]['hours'][hour]['prec_mm'] for hour in range(18,24)])/6, 2)
      avg_soil_temp = round(sum([arr[day]['hours'][hour]['soil_temp'] for hour in range(0,24)])/23, 2)
      avg_soil_prec = round(sum([arr[day]['hours'][hour]['soil_moisture'] for hour in range(0,24)])/23, 2)

      values = [name_of_loc, 'Ярославская область', max_temp_pr, min_temp_pr, avg_temp_pr, wind_gust_pr, wind_speed_temp, precipation_pred_24, precipation_pred_0_6,precipation_pred_6_12, precipation_pred_12_18, precipation_pred_18_24,avg_soil_temp,avg_soil_prec]
      parse_data(values, day, list_of_stations)
  except:
      pass



list_of_stations.sort(key=lambda x: x.name, reverse=False) # arrange list by station name (secondary order by days ago)
scores={}
for station in list_of_stations:
	if station.name in scores:
		scores[station.name]+=station.gen_score() ###5. generate simple scores for each station
	else:
		scores[station.name]=station.gen_score()

# outfile=open("scores_predicted.txt",'w',encoding='cp1251')
for w in sorted(scores, key=scores.get, reverse=True):  # save record of the scores
  # outfile.write("%s, %d\n" %(w, scores[w]))
  print("%s, %d" %( w, scores[w]))
# outfile.close()



### makes a map file with color coded points
station_location={
  'Тутаевский район':'57.957837, 39.815929',
  'Даниловский район':'58.325317, 39.847483',
  'Пошехонский район':'58.65531, 39.124423',
  'Грязовецкий район':'58.661024, 40.618564',
  'Чухломский район':'58.568543, 42.945968',
  'Антроповский район':'58.028759, 43.356216',
  'Варнавинский район':'57.53087, 44.595524',
  'округ Бор':'56.487069, 44.73754',
  'Фурмановский район':'57.208012, 40.787955',
  'Комсомольский район':'56.958759, 40.450125',
  'округ Переславль-Залесский':'57.049997, 38.519278',
  'Большесельский район':'57.592816, 38.763872',
  'деревня Петрилово':'57.044093, 38.505694'
}

# Calculate some statistics to describe the distribution of scores in order to color the pins

def variance(data, ddof=0):
	n = len(data)
	mean = sum(data) / n
	return sum((x - mean) ** 2 for x in data) / (n - ddof)

def stdev(data):
	var = variance(data)
	std_dev = math.sqrt(var)
	return std_dev

maximum_score=max(scores.values())
minimum_score=min(scores.values())
st_dev=stdev(scores.values())
mean=sum(scores.values())/len(scores.values())

# low_score=mean-(.675*st_dev)  # below 1st quartile -> red
low_score = 1
mid_score = 2.5
# mid_score=mean                # 1st to 2nd quartile -> orange
# high_score=mean+(.675*st_dev) # 2nd to 3rd quartile -> yellow
high_score=3
                              # 3rd to 4th quartile -> green

for station in scores:
    data_of_location = 0
    if scores[station]<=low_score:
        pin_color = "red"
    elif scores[station] > low_score and scores[station] <= mid_score:
        pin_color="orange"
    elif scores[station] > mid_score and scores[station] <= high_score:
        pin_color="yellow"
        data_of_location = {"date": int(time.time()),
                            "location_name": f"В этом месте могут быть грибы с вероятностью {round(scores[station] * 100, 1)} %",
                            "lat": station_location[station].split(', ')[0],
                            "lon": station_location[station].split(', ')[1], "url":'https://i.ibb.co/qmJLbpg/mush-find.png'}
    elif scores[station] > high_score:
        pin_color="green"
        data_of_location = {"date": int(time.time()),
                            "location_name": f"В этом месте могут быть грибы с вероятностью {round(scores[station] * 100, 1)} %",
                            "lat": station_location[station].split(', ')[0],
                            "lon": station_location[station].split(', ')[1], "url":'https://i.ibb.co/qmJLbpg/mush-find.png'}
    # print(station_location[station])
    # print(station_location[station].split(', ')[1])
    if data_of_location != 0:
        db.child("mushrooms").push(data_of_location)

# legend_lat=58.344869
# legend_long=37.991323