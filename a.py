import torch
import numpy as np
from torch.autograd import Variable

w_raw = np.array([[2,3],[2,3]])
w = Variable(torch.from_numpy(w_raw).float(), requires_grad=True)
x = Variable(torch.ones(2, 2))
xx = Variable(torch.ones(2, 2)) * 2

x[:2] = xx[:2]
print(x)
# y = torch.mm(x, w)
# z = y.repeat(3,1)
# print(z)
# out = z.mean()
#
# out.backward()
#
# print(w.grad)
