import os
import csv
import pandas as pd
from tensorflow.keras.models import model_from_json
import joblib
import numpy as np
import matplotlib.pyplot as plt


def model_load(path: str, name: str):

    # 加载 json
    model_json_path = os.path.abspath(os.path.join(path, name + ".json"))
    json_file = open(model_json_path, "r")
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)

    # 加载权重
    model_path = os.path.abspath(os.path.join(path, name + ".h5"))
    model.load_weights(model_path)

    return model


def model_predict(audio_path: str, opensmile_path: str, model) -> None:
    
    class_labels = ['angry', 'fear', 'happy', 'neutral', 'sad', 'surprise']

    # 获取opensmile特征
    get_features(audio_path, opensmile_path)

    # 加载opensmile特征，并标准化
    test_features = load_features()
    test_features = np.reshape(test_features, (test_features.shape[0], 1, test_features.shape[1]))

    # 模型预测
    result = np.argmax(model.predict(test_features), axis=1)
    result_prob = predict_proba(model, test_features)
    print('Recogntion: ', class_labels[int(result)])
    print('Probability: ', result_prob)
    # radar(result_prob, class_labels)

    return class_labels[int(result)]


def predict_proba(model, features: np.ndarray):

    return model.predict(features)[0]



def radar(data_prob: np.ndarray, class_labels: list) -> None:
    """
    绘制置信概率雷达图

    Args:
        data_prob (np.ndarray): 概率数组
        class_labels (list): 情感标签
    """
    angles = np.linspace(0, 2 * np.pi, len(class_labels), endpoint=False)

    # 闭合
    data = np.concatenate((data_prob, [data_prob[0]]))
    angles = np.concatenate((angles, [angles[0]]))
    class_labels = class_labels + [class_labels[0]]

    fig = plt.figure()

    # polar参数
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, data, "bo-", linewidth=2)
    ax.fill(angles, data, facecolor="r", alpha=0.25)
    ax.set_thetagrids(angles * 180 / np.pi, class_labels)
    ax.set_title("Emotion Recognition", va="bottom")

    # 设置雷达图的数据最大值
    ax.set_rlim(0, 1)
    ax.grid(True)
    plt.show()


def get_features(audio_path: str, opensmile_path: str):

    feature_path = './features/predict.csv'
    audio_path_abs = os.path.abspath(audio_path)

    # 写表头
    writer = csv.writer(open(feature_path, 'w'))
    first_row = ['label']
    for i in range(1, 1582 + 1):
        first_row.append(str(i))
    writer.writerow(first_row)

    # 特征数据提取
    writer = csv.writer(open(feature_path, 'a+'))
    print('Opensmile extracting...')

    opensmile_config_path = os.path.join(opensmile_path, 'config', 'is09-13', 'IS10_paraling.conf')
    single_feat_path = './features/single_feature.csv'
    single_feat_path_abs = os.path.abspath(single_feat_path)

    cmd = 'cd ' + opensmile_path + '/bin' + ' && ./SMILExtract -C ' \
        + opensmile_config_path + ' -I ' + audio_path_abs + ' -O ' \
        + single_feat_path_abs + ' -appendarff 0'
    print("Opensmile cmd: ", cmd)
    os.system(cmd)

    reader = csv.reader(open(single_feat_path,'r'))
    rows = [row for row in reader]
    last_line = rows[-1]
    feature_vector = last_line[1: 1582 + 1]
    feature_vector.insert(0, '-1')

    # 写特征数据
    writer.writerow(feature_vector)
    print('Opensmile extract done.')


def load_features():

    feature_path = './features/predict.csv'

    # 加载特征数据
    df = pd.read_csv(feature_path)
    features = [str(i) for i in range(1, 1582 + 1)]
    X = df.loc[:,features].values

    # 标准化
    scaler_path = './models/SCALER_OPENSMILE.m'
    scaler = joblib.load(scaler_path)
    X = scaler.transform(X)

    return X


if __name__ == '__main__':
    audio_path = './audios/chunk/chunk-00-loud50.wav'
    opensmile_path = '/home/pi/opensmile-3.0.2'

    # 加载模型
    model_path = './models'
    model_name = 'LSTM_OPENSMILE_IS10'
    model = model_load(model_path, model_name)

    # 模型预测
    model_predict(audio_path, opensmile_path, model)
