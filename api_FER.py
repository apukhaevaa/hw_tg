from flask import Flask, request, make_response, jsonify
import requests
from fer import FER
from PIL import Image
from io import BytesIO
import requests
import numpy as np
import time
from moviepy.editor import *


# создадим экземпляр класса Flask
app = Flask(__name__)

# загружаем модель FER 
detector = FER()



# функция получения изображения по ссылке и конвертация в RGB
def read_image_from_url(url):
    response = requests.get(url, stream=True)
    img = np.asarray(Image.open(BytesIO(response.content)).convert('RGB'))
    return img


# стартовая страница с функцией-обработчиком
@app.route("/")
def hello():
    return "Добро пожаловать в API модели нейронной сети!"


# привязываем к адресу '/detect_emotion' функцию для
# обработки фотографии при помощи нейросети FER
@app.route('/detect_emotion', methods=['POST'])
def detect_emotion():

    # проверка корректности запросв
    if 'url' in request.json:

        # достаем то, что хранится под ключем url
        image_url = request.json['url']

        # скачиваем изображение и переводим в RGB
        img = read_image_from_url(image_url)
        time.sleep(5)

    # выполняем распознавание и возвращаем результат
    resp = detector.detect_emotions(img)
    return make_response(jsonify({'message': resp[0]['emotions']}), 200)


if __name__ == '__main__':
    app.run(debug=True)



    