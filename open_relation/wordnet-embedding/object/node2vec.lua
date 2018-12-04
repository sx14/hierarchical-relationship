require 'nngraph'
require 'nn'
require 'dpnn'
require 'Dataset'
require 'hdf5'

dataset_name = 'pascal'
featureDimension = 600


datasetPath = dataset_name .. '_dataset/contrastive_trans.t7'
weights = torch.load('word_embedding_weights_' .. dataset_name .. '.t7')


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

myFile = hdf5.open('word_vec_' .. dataset_name .. '.h5', 'w')

myFile:write('word_vec', torch.Tensor(fs))
myFile:close()