from __future__ import division
from __future__ import print_function

import os
import json
import time
import argparse
import numpy as np
import scipy.sparse as sp
from tqdm import tqdm

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
            self.fc00=nn.Linear(nfeat,nhid)
            self.fc01=nn.Linear(nhid,nhid)
            self.fc10=nn.Linear(nfeat,nhid)
            self.fc11=nn.Linear(nhid,nhid)
            self.gcn0=GCN(nfeat=nhid,nhid=nhid,dropout=args.dropout)
            self.gcn1=GCN(nfeat=nhid,nhid=nhid,dropout=args.dropout)
            self.fc02=nn.Linear(nhid,nhid)
            self.fc03=nn.Linear(nhid,nhid)
            self.fc12=nn.Linear(nhid,nhid)
            self.fc13=nn.Linear(nhid,nhid)
        else:
            self.fc00=nn.Linear(nfeat,nhid)
            self.fc01=nn.Linear(nhid,nhid)
            self.fc10=nn.Linear(nfeat,nhid)
            self.fc11=nn.Linear(nhid,nhid)
        self.fc0=nn.Linear(nhid*2,nhid*2)
        self.fc1=nn.Linear(nhid*2,nhid*2)
        self.fc2=nn.Linear(nhid*2,nhid*2)
        self.fc3=nn.Linear(nhid*2,nhid*2)
        self.fc4=nn.Linear(nhid*2,2)

        for m in self.modules():
            if isinstance(m,nn.Linear):
                torch.nn.init.xavier_uniform_(m.weight)
                m.bias.data.fill_(0.00)

    def forward(self,gpf):
        if self.Use_GCN:
            x0=F.relu(self.fc01(F.relu(self.fc00(gpf[1]))))
            x1=F.relu(self.fc11(F.relu(self.fc10(gpf[3]))))
            x0=self.gcn0(x0,gpf[0])
            x1=self.gcn1(x1,gpf[2])
            x0=F.relu(self.fc03(F.relu(self.fc02(x0))))
            x1=F.relu(self.fc13(F.relu(self.fc12(x1))))
        else:
            x0=F.relu(self.fc01(F.relu(self.fc00(gpf[1]))))
            x1=F.relu(self.fc11(F.relu(self.fc10(gpf[3]))))
        x1=torch.sum(x1,dim=0,keepdim=True).repeat(x0.size()[0],1)
        x=torch.cat((x0,x1),dim=1)
        x=F.relu(self.fc0(x))
        x=F.relu(self.fc1(x))
        x=F.relu(self.fc2(x))
        x=F.relu(self.fc3(x))
        x=self.fc4(x)
        return x

def load_dataset(args):
    graph_pairs_formatted=[]
    dataset_path='../data/%s'%(args.dataset)
    dir_list=os.listdir(dataset_path)
    seqs=[x[:-14] for x in dir_list if (x.endswith('_sequence.json')) and ('%s_target.json'%(x[:-14]) in dir_list)]
    counter=[0,0,0]
    for k in tqdm(range(len(seqs))):
        seq=seqs[k]
        with open('%s/%s_sequence.json'%(dataset_path,seq)) as json_data:
            data_seq=json.load(json_data)
        with open('%s/%s_target.json'%(dataset_path,seq)) as json_data:
            data_tar=json.load(json_data)
        adj_tar,features_tar=format_graph_data(data_tar)
        node_names_tar=[x['id'] for x in data_tar['nodes']]
        for step in data_seq['sequence']:
            data_cur={'nodes':[],'links':[]}
            for nid in step['faces']:
                for node in data_tar['nodes']:
                    if nid==node['id']:
                        data_cur['nodes'].append(node)
            for eid in step['edges']:
                for link in data_tar['links']:
                    if eid==link['id']:
                        data_cur['links'].append(link)
            adj_cur,features_cur=format_graph_data(data_cur)
            labels_now=np.zeros((len(node_names_tar)),dtype=int)
            labels_now[node_names_tar.index(step['action'])]=1
            labels_now=torch.LongTensor(labels_now)
            graph_pairs_formatted.append([adj_tar,features_tar,adj_cur,features_cur,labels_now])
            counter[0]+=1
            counter[1]+=len(node_names_tar)
            counter[2]+=len(step['faces'])
    print('total graph pairs: %d, total nodes: %d - %d'%(counter[0],counter[1],counter[2]))
    print('All zero accuracy: %.3f%%'%(100.0-counter[0]/counter[1]*100.0))
    return graph_pairs_formatted

def format_graph_data(data):
    surf_type_dict={'ConeSurfaceType':2,'CylinderSurfaceType':1,'EllipticalConeSurfaceType':6,
    'EllipticalCylinderSurfaceType':5,'NurbsSurfaceType':7,'PlaneSurfaceType':0,
    'SphereSurfaceType':3,'TorusSurfaceType':4}
    node_names=[x['id'] for x in data['nodes']]
    # surface type
    features_SurTyp=np.zeros((len(node_names),8))
    for i in range(len(data['nodes'])):
        features_SurTyp[i,surf_type_dict[data['nodes'][i]['surface_type']]]=1
    # points
    features_Poi=np.zeros((len(node_names),len(data['nodes'][0]['points'])))
    for i in range(len(data['nodes'])):
        features_Poi[i,:]=data['nodes'][i]['points']
    # normals
    features_Nor=np.zeros((len(node_names),len(data['nodes'][0]['normals'])))
    for i in range(len(data['nodes'])):
        features_Nor[i,:]=data['nodes'][i]['normals']
    # trimming_mask
    features_TriMas=np.zeros((len(node_names),len(data['nodes'][0]['trimming_mask'])))
    for i in range(len(data['nodes'])):
        features_TriMas[i,:]=data['nodes'][i]['trimming_mask']
    features=np.concatenate((features_SurTyp,features_Poi,features_Nor,features_TriMas),axis=1)
    features=torch.FloatTensor(features)
    # edges
    edges_from,edges_to=[],[]
    for link in data['links']:
        if (link['source'] not in node_names) or (link['target'] not in node_names):
            continue
        idx1=node_names.index(link['source'])
        idx2=node_names.index(link['target'])
        edges_from.append(idx1)
        edges_to.append(idx2)
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
    # TODO: shuffle & batch
    for epoch in range(args.epochs):
        loss,acc=0,[0,0]
        for iter in tqdm(range(len(graph_pairs_formatted))):
            optimizer.zero_grad()
            output=model(graph_pairs_formatted[iter])
            loss_now=F.cross_entropy(output,graph_pairs_formatted[iter][4],reduction='sum')
            loss_now.backward()
            optimizer.step()
            acc=accuracy(acc,output,graph_pairs_formatted[iter][4])
            loss=loss+loss_now.item()
        #scheduler.step(loss/acc[1])
        print('Epoch: {:04d}'.format(epoch+1),'loss: {:.4f}'.format(loss/acc[1]),'accuracy: {:.3f}'.format(acc[0]/acc[1]*100.0))

if __name__=="__main__":
    # args
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-cuda',action='store_true',default=False,help='Disables CUDA training.')
    parser.add_argument('--dataset',type=str,default='RegraphPerFace_01',help='Dataset name.')
    parser.add_argument('--seed',type=int,default=42,help='Random seed.')
    parser.add_argument('--epochs',type=int,default=1000,help='Number of epochs to train.')
    parser.add_argument('--lr',type=float,default=0.0001,help='Initial learning rate.')
    parser.add_argument('--weight_decay',type=float,default=5e-4,help='Weight decay (L2 loss on parameters).')
    parser.add_argument('--hidden',type=int,default=256,help='Number of hidden units.')
    parser.add_argument('--dropout',type=float,default=0.1,help='Dropout rate.')
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
