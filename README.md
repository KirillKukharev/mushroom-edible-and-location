# check mushroom edibility and search location
Diploma project. This repository contains simple web site, which was written on python using flask, scripts for retrieve data from vk and Yadex weather.

# Structure 
 1. flask-server folder contains site files to check if mushroom edible or not by photo. Also you can search mushroom on mushroom map, that gets data from yandex.weather and vk pages and groups.
 2. mushroom-location folder contains Vkontakte scraper and Yandex.Weather scraper. Vkontakte scraper gets data about mushrooms images and geolocations.
Yandex.Weather retrieve data about weather. It gets parameters such as soil moisture, soil temperature, temperature and etc. After retrieved data program calculate score that become to mushrooms condition and define for each place percent of possible growing of mushroom.
 3. train folder consists files that relate of train models to detect mushrooms on photo and classify mushroom species. This info helps to chose if the mushroom is edible or not.
You can download dataset for train and weights of trained models by [this link](https://drive.google.com/drive/folders/1-E2Co9ZdZYGQk-G4aeE_QWtv4Mu30pLJ?usp=sharing).