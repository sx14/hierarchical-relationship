import os
import re
import json
import numpy as np
from nltk.corpus import wordnet
import path_config

label2wn_path = os.path.join(path_config.RELATION_SAVE_ROOT, 'label2wn.json')
with open(label2wn_path, 'r') as label2wn_file:
    label2wn = json.load(label2wn_file)

all_nouns = set()
for label in label2wn.keys():
    # add all labels
    all_nouns.add(label)
    wns = label2wn[label]
    for wn in wns:
        # add all directly linked wn, include stub
        all_nouns.add(wn)
        wn_parts = wn.split('.')
        if wn.split('.')[1] == 'x':  # stub wn
            continue
        else:
            synset = wordnet.synset(wn)
            for p in synset.hypernym_paths():
                for w in p:
                    # add wn on hypernym paths
                    all_nouns.add(w.name())
all_nouns = list(all_nouns)


# get mapping of synset id to index
id2index = {}
for i in range(0, len(all_nouns)):
    n = all_nouns[i]
    id2index[n] = i

# get hypernym relations
hypernyms = []
for label in label2wn.keys():
    wns = label2wn[label]
    for wn in wns:
        hypernyms.append([id2index[label], id2index[wn]]) # label -> wn
for n in all_nouns:
    n_split = re.match(r'(\w+).(\w+).(\d+)', n)
    if n_split is not None and n_split.group(2) != 'x':
        synset = wordnet.synset(n)
        for h in synset.hypernyms() + synset.instance_hypernyms():
            hypernyms.append([id2index[synset.name()], id2index[h.name()]])
hypernyms = np.array(hypernyms)
# save hypernyms
import h5py

f = h5py.File('exp_dataset/wordnet_with_vs.h5', 'w')
f.create_dataset('hypernyms', data=hypernyms)
f.close()
# save list of synset names
import json
wn2index_save_path = os.path.join(path_config.RELATION_SAVE_ROOT, 'wn2index.json')
json.dump(id2index, open(wn2index_save_path, 'w'))
json.dump(all_nouns, open('exp_dataset/synset_names_with_vs.json', 'w'))