require 'nngraph'
require 'nn'
require 'dpnn'
require 'Dataset'
require 'hdf5'

featureDimension = 300
datasetPath = 'dataset/contrastive_trans.t7'
weights = torch.load('dataset/word_embedding_weights_wn.t7')
dataset = torch.load(datasetPath)
lookup = nn.LookupTable(dataset.numEntities, featureDimension)
lookup.weight = weights:double()
fs = torch.Tensor(dataset.numEntities, featureDimension)
embedding = nn.Sequential():add(lookup)
for i=1, dataset.numEntities do
  input = torch.Tensor({i})
  f = embedding:forward(input):clone()
  fs[i] = f
end
local myFile = hdf5.open('dataset/word_vec_wn.h5', 'w')
myFile:write('word_vec', torch.Tensor(fs))
myFile:close()
