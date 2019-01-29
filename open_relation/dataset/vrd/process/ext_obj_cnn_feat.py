"""
step5: extract CNN feature for image region using pretrained CNN
"""
import os
import json
import random
import pickle
import numpy as np
import caffe
import cv2
from lib.fast_rcnn.test import im_detect
from open_relation.dataset.dataset_config import DatasetConfig
from open_relation import global_config
from open_relation.dataset.vrd.label_hier.obj_hier import objnet
from open_relation.dataset.vrd.label_hier.pre_hier import prenet

def cal_sample_ratio(label2index, vrd2path, box_labels):
    # instance counter
    label_ins_cnt = np.zeros(len(label2index.keys()))

    # counting
    for img_id in box_labels:
        img_box_labels = box_labels[img_id]
        for box_label in img_box_labels:
            vrd_label = box_label[4]
            label_path = vrd2path[label2index[vrd_label]]
            for l in label_path:
                label_ins_cnt[l] += 1

    # sample at most 1000 instance
    label_sample_ratio = np.ones(label_ins_cnt.shape)
    for i, ins_num in enumerate(label_ins_cnt):
        if ins_num > 1000:
            label_sample_ratio[i] = 1000.0 / ins_num
    return label_sample_ratio


def prepare_object_boxes_and_labels(anno_root, anno_list_path, box_label_path):
    objs = dict()
    with open(anno_list_path, 'r') as anno_list_file:
        anno_list = anno_list_file.read().splitlines()
    for i in range(0, len(anno_list)):
        anno_file_id = anno_list[i]
        print('prepare processing[%d/%d] %s' % (len(anno_list), (i + 1), anno_file_id))
        anno_path = os.path.join(anno_root, anno_list[i]+'.json')
        anno = json.load(open(anno_path, 'r'))
        image_id = anno_list[i]
        anno_objects = anno['objects']
        obj_info = []
        for o in anno_objects:
            xmin = int(o['xmin'])
            ymin = int(o['ymin'])
            xmax = int(o['xmax'])
            ymax = int(o['ymax'])
            obj_info.append([xmin, ymin, xmax, ymax, o['name']])
        objs[image_id] = obj_info
    with open(box_label_path, 'wb') as box_label_file:
        pickle.dump(objs, box_label_file)


def extract_fc7_features(net, img_box_label, img_root, list_path, feature_root,
                         label_list_path, label2index, vrd2wn, vrd2path, sample_ratio):
    # check output file existence
    if os.path.exists(label_list_path):
        os.remove(label_list_path)
    label_list = []

    # loading image file list of current dataset
    with open(list_path, 'r') as list_file:
        image_list = list_file.read().splitlines()

    # for each image file
    for i in range(0, len(image_list)):
        image_id = image_list[i]
        print('fc7 processing[%d/%d] %s' % (len(image_list), (i + 1), image_id))
        if image_id not in img_box_label:
            continue

        # get boxes
        curr_img_boxes = np.array(img_box_label[image_id])
        box_num = curr_img_boxes.shape[0]
        if box_num == 0:
            continue

        # fc7 feature saving path
        feature_id = image_id + '.bin'
        feature_path = os.path.join(feature_root, feature_id)

        if True or not os.path.exists(feature_path):
            # extract fc7
            img = cv2.imread(os.path.join(img_root, image_id+'.jpg'))
            im_detect(net, img, curr_img_boxes[:, :4])
            fc7s = np.array(net.blobs['fc7'].data)

            # dump feature file
            with open(feature_path, 'w') as feature_file:
                pickle.dump(fc7s, feature_file)

        # prepare roidb
        # format:
        # img_id.bin offset label_ind vrd_label_ind
        for box_id in range(0, len(curr_img_boxes)):
            vrd_label = curr_img_boxes[box_id, 4]
            vrd_label_ind = label2index[vrd_label]

            label_list.append(feature_id+' '+str(box_id)+' '+str(vrd_label_ind)+' '+str(vrd_label_ind)+'\n')

            wn_leaf_label = vrd2wn[vrd_label][0]
            wn_leaf_ind = label2index[wn_leaf_label]
            label_list.append(feature_id+' '+str(box_id)+' '+str(wn_leaf_ind)+' '+str(vrd_label_ind)+'\n')

            label_inds = vrd2path[vrd_label_ind]
            # label_inds = random.sample(label_inds, int(len(label_inds) / 3))
            for label_ind in label_inds:
                sample_prob = sample_ratio[label_ind]
                p = np.array([sample_prob, 1-sample_prob])
                sample = np.random.choice([True, False], p=p.ravel())
                if sample:
                    label_list.append(feature_id + ' ' + str(box_id) + ' ' + str(label_ind) + ' ' + str(vrd_label_ind) + '\n')
        if (i+1) % 10000 == 0 or (i+1) == len(image_list):
            with open(label_list_path, 'a') as label_file:
                label_file.writelines(label_list)
            del label_list
            label_list = []
    if len(label_list) > 0:
        with open(label_list_path, 'a') as label_file:
            label_file.writelines(label_list)


def split_a_small_val(val_list_path, length, small_val_path):
    small_val = []
    with open(val_list_path, 'r') as val_list_file:
        val_list = val_list_file.readlines()
        val_list_length = len(val_list)
    for i in range(0, length):
        ind = random.randint(0, val_list_length - 1)
        small_val.append(val_list[ind])
    with open(small_val_path, 'w') as small_val_file:
        small_val_file.writelines(small_val)



def ext_cnn_feat():
    # load cnn
    prototxt = global_config.fast_prototxt_path
    caffemodel = global_config.fast_caffemodel_path
    datasets = ['train', 'test']
    caffe.set_mode_gpu()
    caffe.set_device(0)
    net = caffe.Net(prototxt, caffemodel, caffe.TEST)

    # prepare
    dataset_config = DatasetConfig('vrd')
    target = 'object'
    labelnet = objnet


    # extracting feature
    anno_root = dataset_config.data_config['clean_anno_root']
    img_root = dataset_config.data_config['img_root']
    label_save_root = dataset_config.extra_config[target].label_root
    prepare_root = dataset_config.extra_config[target].prepare_root
    fc7_save_root = dataset_config.extra_config[target].fc7_root
    for d in datasets:
        # prepare labels and boxes
        label_save_path = os.path.join(label_save_root, d + '.txt')
        anno_list = os.path.join(dataset_config.pascal_format['ImageSets'], d + '.txt')
        box_label_path = os.path.join(prepare_root, d + '_box_label.bin')
        prepare_object_boxes_and_labels(anno_root, anno_list, box_label_path)

        # extract cnn feature
        box_label = pickle.load(open(box_label_path, 'rb'))
        label2index = labelnet.label2index()
        raw2wn = labelnet.raw2wn()
        raw2path = labelnet.raw2path()

        # cal sample ratio
        sample_ratio = cal_sample_ratio(label2index, raw2path, box_label)

        extract_fc7_features(net, box_label, img_root, anno_list, fc7_save_root,
                             label_save_path, label2index, raw2wn, raw2path, sample_ratio)

    # split a small val list for quick evaluation
    small_val_path = os.path.join(label_save_root, 'small_val.txt')
    val_path = os.path.join(label_save_root, 'test.txt')
    split_a_small_val(val_path, 1000, small_val_path)