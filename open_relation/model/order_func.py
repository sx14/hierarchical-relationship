import numpy as np
import torch
from torch import nn
from torch.autograd import Variable


def order_sim(hypers, hypos):
    sub = hypers - hypos
    act = nn.functional.relu(sub)
    partial_order_dis = act.norm(p=2, dim=1)
    partial_order_sim = -partial_order_dis
    return partial_order_sim


def order_softmax_loss(batch_scores, pos_neg_inds, labelnet, weights, loss_func):
    punish = labelnet.depth_punish()
    punish_v = Variable(torch.from_numpy(np.array(punish))).float().cuda()

    loss_scores = Variable(torch.zeros(len(batch_scores), len(pos_neg_inds[0]))).float().cuda()
    for i in range(len(batch_scores)):
        # scores = batch_scores[i] * punish_v
        scores = batch_scores[i]
        loss_scores[i] = scores[pos_neg_inds[i]]

    y = Variable(torch.zeros(len(batch_scores))).long().cuda()
    loss = loss_func(loss_scores, y)
    # loss = torch.mean(loss * weights)
    loss = torch.mean(loss)
    acc = 0.0
    for scores in loss_scores:
        p_score = scores[0]
        n_score_max = torch.max(scores[1:])
        if p_score > n_score_max:
            acc += 1
    acc = acc / len(batch_scores)
    return acc, loss


def order_split_loss(batch_scores, pos_neg_inds, labelnet, weights, loss_func):
    acc = 0.0
    # loss_scores = Variable(torch.zeros(len(batch_scores), len(pos_neg_inds[0]))).float().cuda()
    # for i in range(len(batch_scores)):
    #     scores = batch_scores[i]
    #     loss_scores[i] = scores[pos_neg_inds[i]]
    #     p_score = loss_scores[i][0]
    #     n_score_max = torch.max(loss_scores[i][1:])
    #     if p_score > n_score_max:
    #         acc += 1
    # acc = acc / len(batch_scores)
    # y = Variable(torch.zeros(len(batch_scores))).long().cuda()
    # loss_vec = loss_func(loss_scores, y)
    # loss1 = torch.mean(loss_vec)

    loss_vec = Variable(torch.zeros(1)).float().cuda()
    for b in range(batch_scores.size()[0]):
        gt_ind = pos_neg_inds[b][0]
        gt_pathes = labelnet.get_node_by_index(gt_ind).hyper_paths()
        # print(labelnet.get_node_by_index(gt_ind).name())
        gt_path_nodes = set()
        gt_path_inds = set()
        for gt_path in gt_pathes:
            for n in gt_path:
                gt_path_nodes.add(n)
                gt_path_inds.add(n.index())
        # print('=== path ===')
        # print(list(gt_path_inds))
        # print([n.name() for n in gt_path_nodes])
        scores = batch_scores[b]
        for node in gt_path_nodes:
            # print('=== %s ===' % node.name())
            siblings = node.children()
            # print([s.name() for s in siblings])
            if len(siblings) > 1:
                # split
                sib_inds = [s.index() for s in siblings]
                # print(sib_inds)
                sib_scores_v = scores[sib_inds]
                sib_scores_v = sib_scores_v.unsqueeze(0)
                sib_pos_ind = -1
                for i, sib_ind in enumerate(sib_inds):
                    if sib_ind in gt_path_inds:
                        sib_pos_ind = i
                # print(sib_pos_ind)
                sib_pos_ind_v = Variable(torch.zeros(1)).long().cuda()
                sib_pos_ind_v[0] = sib_pos_ind
                # weight = max(10 - node.depth(), 1)
                weight = siblings[sib_pos_ind].get_weight()
                loss = loss_func(sib_scores_v, sib_pos_ind_v)
                loss_vec = torch.cat((loss_vec, loss * weight), 0)
    loss2 = torch.mean(loss_vec[1:])
    # lamda = 0.4
    # return acc, loss1 * lamda + loss2 * (1-lamda)
    return acc, loss2
