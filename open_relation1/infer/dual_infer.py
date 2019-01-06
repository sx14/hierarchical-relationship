# -*- coding: utf-8 -*-
import numpy as np
import sys


class LabelPath:

    def __init__(self, label_inds):
        self._label_num = len(label_inds)
        self._label_inds = label_inds
        self._hit_count = 0.0
        self._label_ranks = dict()
        for label_ind in label_inds:
            self._label_ranks[label_ind] = 0
        self._is_cand = False
        self._set_cand_rank = 0

    def try_hit(self, label_ind, label_rank):
        """
        try to hit label in current path
        :param label_ind: target label index
        :param label_rank: label rank
        :return: current hit ratio
        """
        if label_ind in self._label_ranks:
            self._label_ranks[label_ind] = label_rank
            self._hit_count += 1
        return self._hit_count / self._label_num

    def get_org_label_ind(self):
        return self._label_inds[-1]

    def get_hit_ratio(self):
        return self._hit_count / self._label_num

    def set_cand(self, rank):
        self._is_cand = True
        self._set_cand_rank = rank

    def is_cand(self):
        return self._is_cand

    def get_set_cand_rank(self):
        return self._set_cand_rank

    def get_pred(self):
        pred_label = 0
        for l in self._label_ranks:
            if self._label_ranks[l] > 0:
                pred_label = max(pred_label, l)
        return pred_label


def dual_infer(scores, org2path, label2index):
    """
    双向推断
    1. 自顶向下，按排名从高往低扫描，若有路径在扫描过程中命中率超过指定阈值或扫描数量超过指定阈值则停止扫描，得到命中率最高的若干路径
    2. 自底向上，找出排名最高且最具体的若干label
    3. 比对，产生最终预测结果
    :param scores:
    :param org2path:
    :param label2index:
    :return:
    """

    # all original label indexes
    org_label_inds = set(org2path.keys())

    # all label paths
    all_paths = [LabelPath(path) for path in org2path.values()]

    # find the top 2 original label predictions
    # fill paths with top k predication
    ranked_inds = np.argsort(scores).tolist()
    ranked_inds.reverse()  # descending
    ranks = [0] * len(label2index.keys())  # label_ind 2 rank
    cand_org_inds = []
    cand_path = all_paths[0]

    # thresholds
    top_k = 40

    # searching
    iter = 0
    while len(cand_org_inds) < 2 or iter < top_k:
        rank = iter + 1
        if ranked_inds[iter] in org_label_inds:
            cand_org_inds.append([ranked_inds[iter], rank])
        if iter < top_k:
            # try to fill all paths
            for pi, path in enumerate(all_paths):
                hit_ratio = path.try_hit(ranked_inds[iter], rank)
                if hit_ratio > cand_path.get_hit_ratio():
                    cand_path = path

        ranks[ranked_inds[iter]] = rank
        iter += 1

    # collect ranks of labels on the top 2 paths
    pred_paths = [org2path[org_ind_rank[0]] for org_ind_rank in cand_org_inds]
    pred_path_ranks = [[0] * len(org2path[org_ind_rank[0]]) for org_ind_rank in cand_org_inds]
    for p, path in enumerate(pred_paths):
        for i, l in enumerate(path):
            pred_path_ranks[p][i] = ranks[l]



    # default predication
    final_pred = pred_paths[0][-1]

    top_org_rank_diff = cand_org_inds[1][1] - cand_org_inds[0][1]

    if cand_org_inds[0][1] < 40:
        # 正确的几率很高，除非top1与top2非常相似
        diff_interval = 40
        overlap_ratio_thr = 0.85
    elif cand_org_inds[0][1] < 120:
        diff_interval = 80
        overlap_ratio_thr = 0.4
    else:
        # 正确的几率很低
        # sort candidate paths according to the set_cand_rank
        final_pred = cand_path.get_pred()
        diff_interval = 0

    if top_org_rank_diff < diff_interval:
        # top1 is close to top2
        # cal top1 and top2 overlap
        overlap = set(pred_paths[0]) & set(pred_paths[1])
        overlap_ratio = len(overlap) * 1.0 / min(len(pred_paths[0]), len(pred_paths[1]))

        # overlap is large
        if overlap_ratio > overlap_ratio_thr:
            final_pred = max(overlap)

    return final_pred, cand_org_inds