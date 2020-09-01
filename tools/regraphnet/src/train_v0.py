from __future__ import division
from __future__ import print_function

import os
import json
import time
import argparse
import numpy as np
import scipy.sparse as sp

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

from models.model_gcn import GCN

class NodePointer(nn.Module):
    def __init__(self,nfeat,nhid,nclass,dropout,Use_GCN=True):
        super(NodePointer,self).__init__()
        self.Use_GCN=Use_GCN
        if Use_GCN:
            self.gcn0=GCN(nfeat=nfeat,nhid=args.hidden,dropout=args.dropout)
            self.gcn1=GCN(nfeat=nfeat,nhid=args.hidden,dropout=args.dropout)
        else:
            self.fc00=nn.Linear(nfeat,nhid)
            self.fc01=nn.Linear(nhid,nhid)
            self.fc10=nn.Linear(nfeat,nhid)
            self.fc11=nn.Linear(nhid,nhid)
        self.fc0=nn.Linear(nhid*2,nhid*2)
        self.fc1=nn.Linear(nhid*2,nhid*2)
        self.fc2=nn.Linear(nhid*2,2)

        for m in self.modules():
            if isinstance(m,nn.Linear):
                torch.nn.init.xavier_uniform_(m.weight)
                m.bias.data.fill_(0.01)

    def forward(self,gpf):
        if self.Use_GCN:
            x0=self.gcn0(gpf[1],gpf[0])
            x1=self.gcn1(gpf[3],gpf[2])
        else:
            x0=F.relu(self.fc01(F.relu(self.fc00(gpf[1]))))
            x1=F.relu(self.fc11(F.relu(self.fc10(gpf[3]))))
        x1=torch.sum(x1,dim=0,keepdim=True).repeat(x0.size()[0],1)
        x=torch.cat((x0,x1),dim=1)
        x=F.relu(self.fc0(x))
        x=F.relu(self.fc1(x))
        x=self.fc2(x)
        return x

def load_dataset(args):
    graph_pairs_formatted=[]
    dataset_path='../data/%s'%(args.dataset)
    dir_list=os.listdir(dataset_path)
    seqs=[x[:-14] for x in dir_list if (x.endswith('_sequence.json')) and ('%s_target.json'%(x[:-14]) in dir_list)]
    for seq in seqs:
        with open('%s/%s_sequence.json'%(dataset_path,seq)) as json_data:
            data_seq=json.load(json_data)
        with open('%s/%s_target.json'%(dataset_path,seq)) as json_data:
            data_tar=json.load(json_data)
        node_names=[x['id'] for x in data_tar['nodes']]
        adj_tar,features_tar=format_graph_data(node_names,data_tar['links'])
        for step in data_seq['sequence']:
            links_now=[]
            for e in step['edges']:
                for link in data_tar['links']:
                    if link['id']==e:
                        links_now.append(link)
            adj_cur,features_cur=format_graph_data(step['faces'],links_now)
            labels_now=np.zeros((len(node_names)),dtype=int)
            labels_now[node_names.index(step['action'])]=1
            labels_now=torch.LongTensor(labels_now)
            graph_pairs_formatted.append([adj_tar,features_tar,adj_cur,features_cur,labels_now])
    return graph_pairs_formatted

def format_graph_data(node_names,links_data):
    nf=len(links_data[0]['param_points'])
    features=np.zeros((len(node_names),nf*2))
    edges_from,edges_to=[],[]
    for link in links_data:
        # convert edge features to node features by simple addition
        if link['source'] in node_names:
            idx1=node_names.index(link['source'])
            features[idx1,:nf]+=np.array(link['param_points'])
        if link['target'] in node_names:
            idx2=node_names.index(link['target'])
            features[idx2,nf:]+=np.array(link['param_points'])
        if (link['source'] not in node_names) or (link['target'] not in node_names):
            continue
        edges_from.append(idx1)
        edges_to.append(idx2)
    features=normalize(features)
    features=torch.FloatTensor(features)
    adj=build_adjacency_matrix(len(node_names),edges_from,edges_to)
    adj=normalize(adj+sp.eye(adj.shape[0]))
    adj=sparse_mx_to_torch_sparse_tensor(adj)
    return adj,features

def build_adjacency_matrix(num_nodes,edges_from,edges_to):
    adj=sp.coo_matrix((np.ones(len(edges_from)),(edges_from,edges_to)),shape=(num_nodes,num_nodes),dtype=np.float32)
    adj=adj+adj.T.multiply(adj.T>adj)-adj.multiply(adj.T>adj)
    return adj

def normalize(mx):
    rowsum=np.array(mx.sum(1))
    r_inv=np.power(rowsum,-1).flatten()
    r_inv[np.isinf(r_inv)]=0.
    r_mat_inv=sp.diags(r_inv)
    mx=r_mat_inv.dot(mx)
    return mx

def sparse_mx_to_torch_sparse_tensor(sparse_mx):
    sparse_mx=sparse_mx.tocoo().astype(np.float32)
    indices=torch.from_numpy(np.vstack((sparse_mx.row,sparse_mx.col)).astype(np.int64))
    values=torch.from_numpy(sparse_mx.data)
    shape=torch.Size(sparse_mx.shape)
    return torch.sparse.FloatTensor(indices,values,shape)

def accuracy(acc,output,labels):
    preds=output.max(1)[1].type_as(labels)
    correct=preds.eq(labels).double()
    correct=correct.sum().item()
    acc[0]+=correct
    acc[1]+=len(labels)
    return acc

def train(graph_pairs_formatted,args):
    model.train()
    for epoch in range(args.epochs):
        optimizer.zero_grad()
        loss,acc=0,[0,0]
        for iter in range(len(graph_pairs_formatted)):
            output=model(graph_pairs_formatted[iter])
            loss_now=F.cross_entropy(output,graph_pairs_formatted[iter][4],reduction='sum')
            acc=accuracy(acc,output,graph_pairs_formatted[iter][4])
            loss=loss+loss_now
        loss.backward()
        optimizer.step()
        scheduler.step(loss.item())
        print('Epoch: {:04d}'.format(epoch+1),'loss: {:.4f}'.format(loss.item()/acc[1]),'accuracy: {:.3f}'.format(acc[0]/acc[1]*100.0))

if __name__=="__main__":
    # args
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-cuda',action='store_true',default=False,help='Disables CUDA training.')
    parser.add_argument('--dataset',type=str,default='test',help='Dataset name.')
    parser.add_argument('--seed',type=int,default=42,help='Random seed.')
    parser.add_argument('--epochs',type=int,default=1000,help='Number of epochs to train.')
    parser.add_argument('--lr',type=float,default=0.01,help='Initial learning rate.')
    parser.add_argument('--hidden',type=int,default=128,help='Number of hidden units.')
    parser.add_argument('--dropout',type=float,default=0.0,help='Dropout rate.')
    args=parser.parse_args()
    args.cuda=not args.no_cuda and torch.cuda.is_available()
    # seed
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)
    # data and model
    graph_pairs_formatted=load_dataset(args)
    model=NodePointer(nfeat=graph_pairs_formatted[0][1].size()[1],nhid=args.hidden,nclass=2,dropout=args.dropout)
    optimizer=optim.Adam(model.parameters(),lr=args.lr)
    scheduler=ReduceLROnPlateau(optimizer,'min')
    # cuda
    if args.cuda:
        model.cuda()
        for i in range(len(graph_pairs_formatted)):
            for j in range(5):
                graph_pairs_formatted[i][j]=graph_pairs_formatted[i][j].cuda()
    # train
    train(graph_pairs_formatted,args)
