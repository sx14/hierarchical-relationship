import os
import random
import pickle
import json
import numpy as np
import h5py
import torch


class MyDataset():
    def __init__(self, raw_data_root, list_path, wn_embedding_path, label2path_path, minibatch_size=128):
        # whole dataset
        self._minibatch_size = minibatch_size
        self._raw_data_root = raw_data_root
        self._feature_indexes = []      # index feature: [feature file name, offset]
        self._word_indexes = []         # label index
        # cached feature package
        self._curr_package = dict()
        # number of image_feature file
        self._curr_package_capacity = 3000
        # package bounds
        self._curr_package_start_fid = 0
        self._next_package_start_fid = 0
        # _curr_package_cursor indexes _curr_package_feature_indexes
        self._curr_package_cursor = 0
        # random current package feature indexes of the whole feature list
        self._curr_package_feature_indexes = []
        # word2vec
        wn_embedding_file = h5py.File(wn_embedding_path, 'r')
        self._wn_embedding = np.array(wn_embedding_file['word_vec'])
        self._wn_feature_length = len(self._wn_embedding[0])
        # label2path
        with open(label2path_path, 'r') as label2path_file:
            self._label2path = json.load(label2path_file)
        with open(list_path, 'r') as list_file:
            f_list = list_file.read().splitlines()
        for item in f_list:
            # image id, offset, hier_label_index, vs_label_index
            item_info = item.split(' ')
            feature_file = item_info[0]
            item_id = int(item_info[1])
            item_word_index = int(item_info[2])
            item_label_index = int(item_info[3])
            # label numbers [hier_label_index, vs_label_index]
            self._word_indexes.append([item_word_index, item_label_index])
            # feature indexes [feature file name, offset]
            self._feature_indexes.append([feature_file, item_id])

    def init_package(self):
        self._next_package_start_fid = 0
        self._curr_package_start_fid = 0
        self._curr_package_cursor = 0
        self._curr_package_feature_indexes = []

    def __len__(self):
        return len(self._feature_indexes)

    def load_next_feature_package(self):
        print('Loading features into memory ......')
        del self._curr_package          # release memory
        self._curr_package = dict()     # feature_file -> [f1,f2,f3,...]
        self._curr_package_start_fid = self._next_package_start_fid
        while len(self._curr_package.keys()) < self._curr_package_capacity:
            if self._next_package_start_fid == len(self._feature_indexes):
                break
            # fill feature package
            next_feature_file, _ = self._feature_indexes[self._next_package_start_fid]
            if next_feature_file not in self._curr_package.keys():
                feature_path = os.path.join(self._raw_data_root, next_feature_file)
                with open(feature_path, 'rb') as feature_file:
                    features = pickle.load(feature_file)
                    self._curr_package[next_feature_file] = features
            self._next_package_start_fid += 1
        self._curr_package_feature_indexes = np.arange(self._curr_package_start_fid, self._next_package_start_fid)
        # shuffle the feature indexes of current feature package
        random.shuffle(self._curr_package_feature_indexes)
        # init package index cursor
        self._curr_package_cursor = 0

    def minibatch2(self):
        # generate minibatch from current feature package
        vfs = []
        p_wfs = []
        n_wfs = []
        gts = []
        if self._curr_package_cursor == len(self._curr_package_feature_indexes):
            # current package finished, load another 4000 feature files
            self.load_next_feature_package()
        if self._curr_package_cursor < len(self._curr_package_feature_indexes):
            fid = self._curr_package_feature_indexes[self._curr_package_cursor]
            feature_file, offset = self._feature_indexes[fid]
            vf = self._curr_package[feature_file][offset]
            positive_label_index = self._word_indexes[fid][0]
            p_wf = self._wn_embedding[positive_label_index]
            self._curr_package_cursor += 1
            positive_labels = self._label2path[unicode(self._word_indexes[fid][1])]
            vfs = np.tile(vf, (len(self._wn_embedding), 1))
            n_wfs = self._wn_embedding
            p_wfs = np.tile(p_wf, (len(self._wn_embedding), 1))
            gts = np.tile([1], (len(self._wn_embedding), 1))

        vfs = torch.from_numpy(np.array(vfs)).float()
        p_wfs = torch.from_numpy(np.array(p_wfs)).float()
        n_wfs = torch.from_numpy(np.array(n_wfs)).float()
        gts = torch.from_numpy(np.array(gts)).float()
        return vfs, p_wfs, n_wfs, gts

    def minibatch1(self):
        # generate minibatch from current feature package
        vf_num = 30
        # negative_label_num = self._minibatch_size / vf_num
        negative_label_num = 2000
        vfs = np.zeros((vf_num * negative_label_num, 4096))
        p_wfs = np.zeros((vf_num * negative_label_num, self._wn_feature_length))
        n_wfs = np.zeros((vf_num * negative_label_num, self._wn_feature_length))
        gts = np.ones((vf_num * negative_label_num, 1))
        for v in range(0, vf_num):
            if self._curr_package_cursor == len(self._curr_package_feature_indexes):
                # current package finished, load another 4000 feature files
                self.load_next_feature_package()
            if self._curr_package_cursor == len(self._curr_package_feature_indexes):
                vfs = vfs[:v * negative_label_num]
                p_wfs = p_wfs[:v * negative_label_num]
                n_wfs = n_wfs[:v * negative_label_num]
                gts = gts[:v * negative_label_num]
                break
            fid = self._curr_package_feature_indexes[self._curr_package_cursor]
            feature_file, offset = self._feature_indexes[fid]
            vf = self._curr_package[feature_file][offset]
            positive_label_index = self._word_indexes[fid][0]
            p_wf = self._wn_embedding[positive_label_index]
            self._curr_package_cursor += 1
            all_negative_labels = list(set(range(0, len(self._wn_embedding))) -
                                   set(self._label2path[unicode(self._word_indexes[fid][1])]))
            negative_labels = random.sample(all_negative_labels, negative_label_num)
            part_n_wfs = self._wn_embedding[negative_labels]
            vfs[v*negative_label_num:(v+1)*negative_label_num] = vf
            p_wfs[v*negative_label_num:(v+1)*negative_label_num] = p_wf
            n_wfs[v*negative_label_num:(v+1)*negative_label_num] = part_n_wfs
            gts[v*negative_label_num:(v+1)*negative_label_num] = [1]

        vfs = torch.from_numpy(np.array(vfs)).float()
        p_wfs = torch.from_numpy(np.array(p_wfs)).float()
        n_wfs = torch.from_numpy(np.array(n_wfs)).float()
        gts = torch.from_numpy(np.array(gts)).float()
        return vfs, p_wfs, n_wfs, gts

    def minibatch_acc(self):
        negative_label_num = 4000
        vfs = np.zeros((self._minibatch_size, 4096))
        p_wfs = np.zeros((self._minibatch_size, self._wn_feature_length))
        v_actual_num = 0
        p_w_set = set()
        for v in range(0, self._minibatch_size):
            if self._curr_package_cursor == len(self._curr_package_feature_indexes):
                # current package finished, load another 4000 feature files
                self.load_next_feature_package()
            if self._curr_package_cursor == len(self._curr_package_feature_indexes):
                vfs = vfs[:v_actual_num]
                p_wfs = p_wfs[:v_actual_num]
                break
            fid = self._curr_package_feature_indexes[self._curr_package_cursor]
            feature_file, offset = self._feature_indexes[fid]
            vfs[v] = self._curr_package[feature_file][offset]
            positive_label_index = self._word_indexes[fid][0]
            p_wfs[v] = self._wn_embedding[positive_label_index]
            p_w_set = p_w_set | set(self._label2path[unicode(self._word_indexes[fid][1])])
            self._curr_package_cursor += 1
            v_actual_num += 1
        all_negative_labels = list(set(range(0, len(self._wn_embedding))) - p_w_set)
        negative_labels = random.sample(all_negative_labels, negative_label_num)
        n_wfs = self._wn_embedding[negative_labels]

        #  vfs: minibatch_size | p_wfs: minibatch_size | n_wfs: negative_label_num
        vfs = torch.from_numpy(np.array(vfs)).float()
        p_wfs = torch.from_numpy(np.array(p_wfs)).float()
        n_wfs = torch.from_numpy(np.array(n_wfs)).float()
        return vfs, p_wfs, n_wfs


    def minibatch_eval(self):
        # generate minibatch from current feature package
        vfs = []
        p_wfs = []
        n_wfs = []
        if self._curr_package_cursor == len(self._curr_package_feature_indexes):
            # current package finished, load another 4000 feature files
            self.load_next_feature_package()
        if self._curr_package_cursor < len(self._curr_package_feature_indexes):
            fid = self._curr_package_feature_indexes[self._curr_package_cursor]
            feature_file, offset = self._feature_indexes[fid]
            vf = self._curr_package[feature_file][offset]
            positive_label_index = self._word_indexes[fid][0]
            p_wf = self._wn_embedding[positive_label_index]
            self._curr_package_cursor += 1
            positive_labels = self._label2path[unicode(self._word_indexes[fid][1])]
            all_negative_labels = list(set(range(0, len(self._wn_embedding))) -
                                       set(positive_labels))
            vfs = [vf]
            n_wfs = self._wn_embedding[all_negative_labels]
            p_wfs = [p_wf]
        vfs = torch.from_numpy(np.array(vfs)).float()
        p_wfs = torch.from_numpy(np.array(p_wfs)).float()
        n_wfs = torch.from_numpy(np.array(n_wfs)).float()
        return vfs, p_wfs, n_wfs


    def has_next_minibatch(self):
        if self._next_package_start_fid == len(self._feature_indexes):
            # the last package
            if self._curr_package_cursor == len(self._curr_package_feature_indexes):
                return False
        return True
