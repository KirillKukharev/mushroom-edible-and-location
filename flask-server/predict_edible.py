import torch
import torch.nn as nn
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import pandas as pd
import numpy as np
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras import layers, models
from tensorflow.keras.layers.experimental import preprocessing

import cv2
import albumentations as A
from albumentations.pytorch import ToTensorV2
from tqdm import tqdm
import matplotlib.pyplot as plt
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


NUM_CLASSES = 2
NUM_QUERIES = 30

class DETRModel(nn.Module):
    def __init__(self, num_classes, num_queries):
        super(DETRModel, self).__init__()
        self.num_classes = num_classes
        self.num_queries = num_queries
        self.model = torch.hub.load('facebookresearch/detr', 'detr_resnet50', pretrained=True)
        self.in_features = self.model.class_embed.in_features
        self.model.class_embed = nn.Linear(in_features=self.in_features, out_features=self.num_classes)
        self.model.num_queries = self.num_queries

    def forward(self, images):
        return self.model(images)


def get_model():
    return DETRModel(num_classes=NUM_CLASSES, num_queries=NUM_QUERIES)


def prepare_model_for_transfer_learning(base_model, num_classes, augmentations=None):
    model = models.Sequential()
    if augmentations:
        model.add(augmentations)

    model.add(base_model)
    model.add(layers.Flatten())

    model.add(layers.Dense(1024, activation='relu', input_dim=512))
    model.add(layers.Dense(512, activation='relu'))
    model.add(layers.Dropout(0.4))
    model.add(layers.Dense(256, activation='relu'))
    model.add(layers.Dropout(0.3))
    model.add(layers.Dense(128, activation='relu'))
    model.add(layers.Dropout(0.2))
    model.add(layers.Dense(num_classes, activation='softmax'))
    return model

def get_pretrained_model(base_model, input_shape, num_classes, augmentations=None):
    pretrained_model = prepare_model_for_transfer_learning(base_model, num_classes, augmentations)
    pretrained_model.build((None, *input_shape))
    return pretrained_model


IMG_WIDTH = 600
IMG_HEIGHT = 600

def get_image(img_path: str):
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    return img.astype(np.float32) / 255.0

def get_mushrooms(model, imgs: list) -> list:
    """Set for DETR model"""
    model.eval()
    every_mushroom = []
    transforms = A.Compose([A.Resize(height=IMG_HEIGHT, width=IMG_WIDTH, p=1.0),
                            ToTensorV2(p=1.0)], p=1.0)

    with torch.no_grad():
        for img in tqdm(imgs):
            img = transforms(image=img)['image']
            outputs = model(img.unsqueeze(0))

            outputs = [{k: v for k, v in outputs.items()}]
            p_boxes = outputs[0]['pred_boxes'][0].detach().cpu().numpy()
            p_boxes = [np.array(box).astype(np.int32) for box in
                       A.augmentations.bbox_utils.denormalize_bboxes(p_boxes, IMG_HEIGHT, IMG_WIDTH)]
            prob = outputs[0]['pred_logits'][0].softmax(1).detach().cpu().numpy()[:, 0]

            sample = img.permute(1, 2, 0).numpy()
            for box, p in zip(p_boxes, prob):
                if p > 0.65:
                    every_mushroom.append(sample[box[1]:box[3] + box[1], box[0]:box[2] + box[0]])
    return every_mushroom

def get_results(models, img, clss):
    results = pd.DataFrame({'Класс': clss})
    for name, model in models:
        if name == 'ResNet50':
            transforms = A.Compose([A.Resize(height=200, width=200, p=1.0)], p=1.0)
        elif name=='VGG16':
            transforms = A.Compose([A.Resize(height=224, width=224, p=1.0)], p=1.0)
        else:
            transforms = A.Compose([A.Resize(height=160, width=160, p=1.0)], p=1.0)

        img = transforms(image=img)['image']
        prediction = model.predict(np.expand_dims(img, axis=0))
        if name == 'VGG16':
          temp_value_in_VGG_for_edible = abs(prediction[0][0])*100
          temp_value_in_VGG_for_poison = abs(prediction[0][1])*100
        else:
          results[name] = np.array(prediction[0] * 100, dtype=int)

    results['VGG16'] = [0]*len(results)
    results['Сумма'] = results.sum(axis=1)
    results = results.sort_values(by=['Сумма'], ascending=False).iloc[:5, :]

    return results

detr_model = get_model()
detr_model.load_state_dict(
    torch.load(BASE_DIR + '/models/detection_mushroom/detr_best_46_a.pth', map_location=torch.device('cpu')))

base_model_resnet = tf.keras.applications.resnet50.ResNet50(include_top=False, weights='imagenet', input_shape=(200, 200, 3))
resnet_model = get_pretrained_model(base_model_resnet, (200, 200, 3), 15)
resnet_model.load_weights(BASE_DIR+'/models/prediction_mushroom/ResNet50_weights.ckpt')

base_model_mobilenet = tf.keras.applications.mobilenet_v2.MobileNetV2(include_top=False, weights='imagenet', input_shape=(160, 160, 3))
mobilenet = get_pretrained_model(base_model_mobilenet, (160, 160, 3), 15)
mobilenet.load_weights(BASE_DIR+'/models/prediction_mushroom/MobileNetV2_weights.ckpt')

model_vgg16 = tf.keras.models.load_model(BASE_DIR+'/models/prediction_mushroom/model_best_weights.h5')


def proccess_img(img_path, img_name):
    images = []
    pic = []
    images.append(get_image(img_path))
    mushrooms = get_mushrooms(detr_model, images)
    if len(mushrooms) == 0:
        edibs=-1
        pic.append(["not_edible_fgsxc.gif", edibs])
        return pic
    train_df = pd.read_csv(BASE_DIR+'/mushroom_classes/train.csv')
    classes = train_df['mushroom'].unique()
    n_classes = len(classes)

    cls_models = [('ResNet50', resnet_model), ('MobileNetV2', mobilenet), ('VGG16', model_vgg16)]

    edible = {"beli", "lisi", "masl", "mayr", "podb", "siro", "dubo"}
    poison = {"dozh", "muho", "pant", "poga", "prek", "ryad", "svin", "zhel"}

    os.chdir(f'{BASE_DIR}/static/downloads/')
    count_mush_in_req = 0
    for mushroom in mushrooms:
        table = get_results(cls_models, mushroom, classes)

        transforms_vgg16 = A.Compose([A.Resize(height=224, width=224, p=1.0)], p=1.0)
        img_vgg = transforms_vgg16(image=mushroom)['image']
        prediction_vgg = model_vgg16.predict(np.expand_dims(img_vgg, axis=0))

        plt.figure(figsize=(15, 6))
        plt.subplot(1, 2, 1)
        plt.imshow(mushroom)
        plt.axis('off')
        plt.subplot(1, 2, 2)
        edible_sum = 0
        poison_sum = 0
        res_net_res_pois = 0
        mobile_net_res_pois = 0
        res_net_res_edible = 0
        mobile_net_res_edible = 0
        for variant in range(3):
            if table.values[variant][0] in edible:
                edible_sum += int(table.values[variant][4])
                res_net_res_edible += int(table.values[variant][1])
                mobile_net_res_edible += int(table.values[variant][2])

            else:
                poison_sum += int(table.values[variant][4])
                res_net_res_pois += int(table.values[variant][1])
                mobile_net_res_pois += int(table.values[variant][2])
        result = [[], []]
        edib = 0
        if edible_sum <= poison_sum:
            edib = 1
            result[0] = ["ядовитый", res_net_res_pois, mobile_net_res_pois, round(prediction_vgg[0][1] * 100),
                         res_net_res_pois + mobile_net_res_pois + round(prediction_vgg[0][1] * 100)]
            result[1] = ["съедобный", res_net_res_edible, mobile_net_res_edible, round(prediction_vgg[0][0] * 33),
                         res_net_res_edible + mobile_net_res_edible + round(prediction_vgg[0][0] * 33)]
        else:
            result[0] = ["съедобный", res_net_res_edible, mobile_net_res_edible, round(prediction_vgg[0][0] * 100),
                         res_net_res_edible + mobile_net_res_edible + round(prediction_vgg[0][0] * 100)]
            result[1] = ["ядовитый", res_net_res_pois, mobile_net_res_pois, round(prediction_vgg[0][1] * 33),
                         res_net_res_pois + mobile_net_res_pois + round(prediction_vgg[0][1] * 33)]

        ############
        ax_table = plt.table(cellText=result, colLabels=table.columns,
                             loc='center', bbox=[0, 0, 1, 1])
        ax_table.auto_set_font_size(False)
        ax_table.set_fontsize(13)
        plt.axis('off')
        plt.tight_layout()
        count_mush_in_req+=1
        pic.append([f'{str(img_name[:-4])}_{count_mush_in_req}.png', edib])
        plt.savefig(f'{str(img_name[:-4])}_{count_mush_in_req}.png')
    return pic

