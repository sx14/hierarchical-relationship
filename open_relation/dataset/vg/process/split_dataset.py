"""
step4: split the whole dataset as train, val and test.
next: ext_cnn_feature.py
"""
import os
from open_relation.dataset.dataset_config import DatasetConfig


def split_dataset():
    vg_config = DatasetConfig('vg')
    anno_root = vg_config.data_config['clean_anno_root']
    split_list_root = vg_config.pascal_format['JPEGImages']
    anno_sum = len(os.listdir(anno_root))

    # TODO
    val_capacity = -1
    test_capacity = -1
    # TODO

    train_capacity = anno_sum - val_capacity - test_capacity
    anno_list = os.listdir(anno_root)
    # random.shuffle(anno_list)
    dataset_list = {
        'train': anno_list[0:train_capacity],
        'val': anno_list[train_capacity:train_capacity+val_capacity],
        'test': anno_list[train_capacity+val_capacity:anno_sum]
    }
    for d in dataset_list:
        image_id_list = []
        ls = dataset_list[d]
        for l in ls:
            image_id_list.append(l.split('.')[0]+'\n')
        list_file_path = os.path.join(split_list_root, d+'.txt')
        with open(list_file_path, 'w') as list_file:
            list_file.writelines(image_id_list)