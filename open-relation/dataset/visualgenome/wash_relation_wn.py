#coding=utf-8
import os
import json
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet as wn

legal_pos_list = ['IN', 'JJ', 'JJR', 'JJS', 'RP', 'TO', 'NN', 'NNS',    # 介词，形容词，比较级，最高级，虚词，to，名词，名词复数
                  'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']              # 动词，过去式，现在分词，过去分词，现在非三单，现在三单


def wash_relation_label(org_anno_root, output_anno_root):
    label_map = []
    anno_list = os.listdir(org_anno_root)
    anno_total = len(anno_list)
    lemmatizer = WordNetLemmatizer()
    for i in range(0, anno_total):  # collect
        anno_file_name = anno_list[i]
        print('washing[%d/%d] : %s' % (anno_total, (i + 1), anno_file_name))
        org_anno_path = os.path.join(org_anno_root, anno_file_name)
        with open(org_anno_path, 'r') as anno_file:
            anno = json.load(anno_file)
        org_relations = anno['relationships']
        relations = []
        for i in range(0, len(org_relations)):
            r = org_relations[i]
            # wash wn
            org_syns = r['synsets']
            syns = []
            for s in org_syns:
                try:
                    # legal wordnet synset
                    wn.synset(s)
                    syns.append(s)
                except ValueError as e:
                    # illegal wordnet synset
                    # abort current synset
                    continue
            r['synsets'] = syns
            # wash label
            predicate = r['predicate']
            if len(predicate) == 0:  # predicate=''
                # try to generate predicate from synsets
                if len(syns) > 0:
                    predicate = syns[0].split['.'][0]
                    r['predicate'] = predicate
                else:
                    # predicate='' and synsets=[]
                    # abort current relation
                    continue
            else:
                # handle predicate
                new_label_words = []
                label_lower = predicate.lower()
                words = nltk.word_tokenize(label_lower)  # split by spaces
                word_pos_list = nltk.pos_tag(words)  # [(word, pos)]
                for word_pos in word_pos_list:
                    word = word_pos[0]
                    pos = word_pos[1]
                    if pos in legal_pos_list:   # legal predicate words
                        if pos.startswith('VB'):
                            org_word = lemmatizer.lemmatize(word, pos='v')  # reshape word to original
                        elif pos.startswith('NN'):
                            org_word = lemmatizer.lemmatize(word, pos='n')  # reshape word to original
                        else:
                            org_word = word
                        new_label_words.append(org_word)
                # merge word list to new predicate
                new_predicate = ' '.join(new_label_words)
                if predicate != new_predicate:
                    label_map.append(predicate + '|' + new_predicate+'\n')
                r['predicate'] = new_predicate
            relations.append(r)
        anno['relationships'] = relations
        output_anno_path = os.path.join(output_anno_root, anno_file_name)
        with open(output_anno_path, 'w') as anno_file:
            json.dump(anno, anno_file, sort_keys=False, indent=4)
    with open('relation_label_map.txt', 'w') as relation_label_map:
        relation_label_map.writelines(label_map)


def wash_relation_wn(relation_label2wn_path):
    """
    run after wash_relation_label
    try to supplement WordNet node
    :param relation_label2wn_path:
    :return:
    """
    with open(relation_label2wn_path, 'r') as label2wn_file:
        label2wn = json.load(label2wn_file)
    wn_stub = 'relation.x.01'
    for label in label2wn.keys():
        wns = label2wn[label]
        if len(''.join(wns)) > 0:
            continue
        wns = []
        words = nltk.word_tokenize(label)  # split by spaces
        word_pos_list = nltk.pos_tag(words)  # [(word, pos)]
        for word_pos in word_pos_list:
            word = word_pos[0]
            pos = word_pos[1]
            if pos in legal_pos_list:
                synsets = wn.synsets(word)
                if len(synsets) > 0:
                    wns.append(synsets[0].name())
        if len(wns) == 0:
            wns.append(wn_stub)
        label2wn[label] = wns
    with open(relation_label2wn_path, 'w') as label2wn_file:
        json.dump(label2wn, label2wn_file,  sort_keys=False, indent=4)




