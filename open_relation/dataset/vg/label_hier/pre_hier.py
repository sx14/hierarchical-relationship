import os
from open_relation.dataset.label_hier import LabelHier
from open_relation.dataset.label_hier import LabelNode
from open_relation.dataset.dataset_config import DatasetConfig


class PreNet(LabelHier):

    def _raw_to_wn(self):
        raw2wn = dict()
        raw_labels = []
        for vg_label in self._raw_labels:
            raw_label, wn_labels = vg_label.split('|')
            raw_labels.append(raw_label)
            wn_labels = wn_labels.split(' ')
            raw2wn[raw_label] = wn_labels
        self._raw_labels = raw_labels
        return raw2wn

    def _construct_hier(self):
        # root node
        # 0 is background
        # TODO: construct predicate label hierarchy
        pass

    def __init__(self, pre_label_path):
        LabelHier.__init__(self, pre_label_path)
        self._raw_to_wn()


dataset_config = DatasetConfig('vg')
label_path = os.path.join(dataset_config.dataset_root, 'predicate_labels.txt')
prenet = PreNet(label_path)

# if __name__ == '__main__':
#     a = PreNet()
#     n = a.get_pre('stand next to')
#     n.show_hyper_paths()