# coding: utf-8
# Team :  uyplayer team
# Author： uyplayer 
# Date ：2020/1/14 下午4:05
# Tool ：PyCharm

'''
Implementation model in paper
'''
from __future__ import print_function
import os
import sys
import argparse

Dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(Dir)

import numpy as np
import word_embedding
import data_convert
from scipy.fftpack import fft,ifft


import torch
import torch.nn as nn
import torch.nn.functional as F
from utils import get_batch_data
from word_embedding import embedding
from data_convert import ConverData
import torch.optim as optim
from torch.autograd import Variable

torch.manual_seed(1)

# AF_LSTM
class AF_LSTM(nn.Module):

    def __init__(self, input_dim, hidden_size, batch_size, embedding_dim, word_embeddings, num_layers=1, is_shuffle = False,bias=True):
        print("Model : AF_LSTM is ready to run")
        super(AF_LSTM, self).__init__()
        self.hidden_size = hidden_size
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim
        self.word_embeddings = word_embeddings
        self.num_layers = num_layers
        self.n_iter = n_iter
        self.bias = bias
        self.is_shuffle = is_shuffle
        self.n_iter = n_iter
        self.input_dim = input_dim
        self.vocab_size = self.word_embeddings.shape[0]
        # model
        #  attention trainable params
        self.w_y = nn.Parameter(torch.randn([self.embedding_dim, self.embedding_dim]))
        self.w_t = nn.Parameter(torch.randn([self.embedding_dim, self.embedding_dim]))
        self.w_p = nn.Parameter(torch.randn([self.embedding_dim, self.embedding_dim]))
        self.w_x = nn.Parameter(torch.randn([self.embedding_dim, self.embedding_dim]))
        self.w_f = nn.Parameter(torch.randn([self.embedding_dim, self.embedding_dim]))
        self.b_f = nn.Parameter(torch.randn(self.embedding_dim))
        self.tanh = nn.Tanh()
        self.softmax = nn.Softmax()
        self.tanh_r = nn.Tanh()
        self.last_Softmax = nn.Softmax()


     # LSTM
    def __lstm(self,input):
        embedding = nn.Embedding(num_embeddings=self.vocab_size, embedding_dim=self.embedding_dim)
        embedding.weight.data.copy_(torch.from_numpy(self.word_embeddings))
        embedding.weight.requires_grad = False
        input_embedding = embedding(Variable(torch.LongTensor(input)))
        self.lstm = nn.LSTM(self.embedding_dim, self.hidden_size, self.num_layers)
        lstm_out, _ = self.lstm(input_embedding)
        return lstm_out

    # aspect_normilization and embedding
    def __aspnor(self,input):
        self.bn = nn.BatchNorm1d(num_features=self.input_dim)
        embedding = nn.Embedding(num_embeddings=self.vocab_size, embedding_dim=self.embedding_dim)
        embedding.weight.data.copy_(torch.from_numpy(self.word_embeddings))
        embedding.weight.requires_grad = False
        input_embedding = embedding(Variable(torch.LongTensor(input)))
        output = self.bn(input_embedding)
        # normal_aspect = torch.sum(output, 1)
        return output

    # Hidenstate_Normalization and embedding
    def __hidennor(self,input):
        bn = nn.BatchNorm1d(num_features=self.input_dim)
        output = bn(input)
        return output

    # calculate  associative memory ；circular correlation
    def __correlation(self, h, s):

        '''
        import numpy as np
        from scipy.fftpack  import fft,ifft
        import matplotlib.pyplot as plt
        a = np.random.rand(83,300)
        b = np.random.rand(1,300)
        A = fft(a)
        B = fft(b)
        C = A*B
        print(C)
        '''
        h = h.data.numpy()
        s = s.data.numpy()
        all = []
        for i in range(len(s)):
            c = fft(h[i]) * fft(s[i])
            all.append(list(c))
        return np.array(all)

    def forward(self,x,s):
        h_lstm_out = self.__lstm(x)
        s__norm = self.__aspnor(s)
        m = self.__correlation(h_lstm_out, s__norm)
        print("m:", type(m))
        m = Variable(torch.LongTensor(torch.from_numpy(m)))
        print("m:", type(m))
        # # attention
        Y = self.tanh(torch.mul(self.w_y,m))
        a = self.softmax(torch.bmm(self.w_t, Y))
        r = torch.matmul(h_lstm_out, a.transpose())
        r = self.tanh_r(torch.bmm(self.w_p, r) + torch.bmm(self.w_x, h_lstm_out))
        x_r = torch.bmm(self.w_f, r) + self.b_f
        y = self.last_Softmax(x_r)
        return y

# train
def train(input_train_x, input_train_y,input_dim, input_aspect, hidden_size, batch_size, embedding_dim,
          word_embeddings, num_layers, is_shuffle = True):

    print("Ready to train")
    # AF_LSTM
    af_lstm = AF_LSTM(input_dim, hidden_size, batch_size, embedding_dim, word_embeddings, num_layers, is_shuffle = True,bias=True)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(af_lstm.parameters(), lr=0.001, momentum=0.9)
    running_loss = 0.0
    for i in range(n_iter):
        for x, y, s in get_batch_data(input_train_x, input_train_y,input_aspect,batch_size,
                                      n_iter=n_iter, is_shuffle=is_shuffle):

            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            outputs = af_lstm(x,s)
            loss = criterion(outputs, y)
            loss.backward()
            optimizer.step()

            # print statistics
            running_loss += loss.item()
            if i % 50 == 0:
                print('[%d, %5d] loss: %.3f' %(i + 1, i + 1, running_loss / 50))
                running_loss = 0.0


print("============================train===========================")

def t(input_train_x, input_train_y,input_dim, input_aspect_train, hidden_size, batch_size, embedding_dim, word_embedding, num_layers, is_shuffle = True):
    print("ok")


# Hyper Parameters
print("===========Hyper Parameters============")
parser = argparse.ArgumentParser()
parser.add_argument('--data_dir', default=os.getcwd() + "/Datasets/raw_data/ABSA-SemEval2014", type=str, help='raw data dir')
parser.add_argument('--input_dim', default=300, type=int,help='input demintions')
parser.add_argument('--hidden_size', default=300, type=int, help='hidden_size')
parser.add_argument('--batch_size', default=5, type=int, help='batch_size')
parser.add_argument('--embedding_dim', default=300, type=int, help='embedding_dim')
parser.add_argument('--num_layers', default=1, type=int, help='num_layers of lstm')
parser.add_argument('--n_iter', default=100, type=int, help='iter num for train loop')
opt = parser.parse_args()
# datasets's dir and get raw data
raw_data = ConverData(opt.data_dir)
trains, tests = ConverData.getData()
# get embendding data
print("*************get embendding data*************")
em = embedding(trains, tests)
train_ids, test_ids, train_y, test_y, train_aps_id, test_aps_id, embedding, word_dict = em.all_data()
# params
input_train_x = train_ids
input_train_y = train_y
input_dim = opt.input_dim
input_aspect_train = train_aps_id
test_aps_id = test_aps_id
hidden_size = opt.hidden_size
batch_size = opt.batch_size
embedding_dim = opt.embedding_dim
word_embeddings = embedding
num_layers = opt.num_layers
n_iter = opt.n_iter
word_dict = word_dict
is_shuffle = False
bias = True

# training
# t(input_train_x, input_train_y,input_dim, input_aspect_train, hidden_size, batch_size, embedding_dim, word_embedding, num_layers, is_shuffle = True)

train(input_train_x, input_train_y,input_dim, input_aspect_train, hidden_size, batch_size, embedding_dim, word_embeddings, num_layers, is_shuffle = False)

print("*************training End**************")