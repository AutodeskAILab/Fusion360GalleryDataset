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

from train_v43 import *

def load_graph_pair(path_tar,path_cur,bbox):
    action_type_dict={'CutFeatureOperation':1,'IntersectFeatureOperation':2,'JoinFeatureOperation':0,'NewBodyFeatureOperation':3,'NewComponentFeatureOperation':4}
    operation_names=['JoinFeatureOperation','CutFeatureOperation','IntersectFeatureOperation','NewBodyFeatureOperation','NewComponentFeatureOperation']
    with open(path_tar) as json_data:
        data_tar=json.load(json_data)
    adj_tar,features_tar=format_graph_data(data_tar,bbox)
    if not path_cur:
        adj_cur,features_cur=torch.zeros((0)),torch.zeros((0))
    else:
        with open(path_cur) as json_data:
            data_cur=json.load(json_data)
        adj_cur,features_cur=format_graph_data(data_cur,bbox)
    graph_pair_formatted=[adj_tar,features_tar,adj_cur,features_cur]
    node_names=[x['id'] for x in data_tar['nodes']]
    return graph_pair_formatted,node_names,operation_names

def inference(graph_pair_formatted,node_names,operation_names,use_gpu=False):
    model.eval()
    with torch.no_grad():
        output_node,output_op=model(graph_pair_formatted,use_gpu=use_gpu)
        output_start=F.softmax(output_node[:,0].view(1,-1),dim=1)
        output_end=F.softmax(output_node[:,1].view(1,-1),dim=1)
        output_op=F.softmax(output_op,dim=1)
    if use_gpu:
        ps=[output_start.data.cpu().numpy()[0,:],output_end.data.cpu().numpy()[0,:],output_op.data.cpu().numpy()[0,:]]
    else:
        ps=[output_start.data.numpy()[0,:],output_end.data.numpy()[0,:],output_op.data.numpy()[0,:]]
    # enumerate all actions
    actions,probs=[],[]
    for i in range(len(node_names)):
        for j in range(len(node_names)):
            for k in range(len(operation_names)):
                actions.append([node_names[i],node_names[j],operation_names[k]])
                probs.append(ps[0][i]*ps[1][j]*ps[2][k])
    actions_sorted,probs_sorted=[],[]
    idx=np.argsort(-np.array(probs))
    for i in range(len(probs)):
        actions_sorted.append(actions[idx[i]])
        probs_sorted.append(probs[idx[i]])
    return actions_sorted,probs_sorted

if __name__=="__main__":
    # args
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-cuda',action='store_true',default=True,help='Disables CUDA training.')
    parser.add_argument('--dataset',type=str,default='RegraphPerFace_05',help='Dataset name.')
    parser.add_argument('--split',type=str,default='train_test',help='Split name.')
    parser.add_argument('--hidden',type=int,default=256,help='Number of hidden units.')
    args=parser.parse_args()
    args.cuda=not args.no_cuda and torch.cuda.is_available()
    # load model
    model=NodePointer(nfeat=708,nhid=args.hidden,Use_GCN=False)
    model.load_state_dict(torch.load('../ckpt/model_v43.ckpt'))
    if args.cuda:
        model.cuda()
    # inference
    t1=time.time()
    for seq in ['31962_e5291336_0054']:
        # load _sequence.json, as an example
        path_seq='../data/%s/%s_sequence.json'%(args.dataset,seq)
        if not os.path.isfile(path_seq):
            continue
        with open(path_seq) as json_data:
            data_seq=json.load(json_data)
        path_tar='../data/%s/%s'%(args.dataset,data_seq['sequence'][-1]['graph'])
        bbox=data_seq['properties']['bounding_box']
        for t in range(len(data_seq['sequence'])):
            # load and format graph data from json files
            if t==0:
                path_cur=None
            else:
                path_cur='../data/%s/%s_%04d.json'%(args.dataset,seq,t-1)
            graph_pair_formatted,node_names,operation_names=load_graph_pair(path_tar,path_cur,bbox)
            if args.cuda:
                for j in range(4):
                    graph_pair_formatted[j]=graph_pair_formatted[j].cuda()
            # inference
            actions_sorted,probs_sorted=inference(graph_pair_formatted,node_names,operation_names,use_gpu=args.cuda)
            print(actions_sorted)
            print(probs_sorted)
    t2=time.time()
    print('%.5f seconds.'%(t2-t1))
