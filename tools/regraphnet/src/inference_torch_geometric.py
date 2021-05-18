from __future__ import division
from __future__ import print_function

import os
import json
import time
import argparse
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from train_torch_geometric import *

def load_graph_pair(path_tar,path_cur,bbox):
    action_type_dict={'CutFeatureOperation':1,'IntersectFeatureOperation':2,'JoinFeatureOperation':0,'NewBodyFeatureOperation':3,'NewComponentFeatureOperation':4}
    operation_names=['JoinFeatureOperation','CutFeatureOperation','IntersectFeatureOperation','NewBodyFeatureOperation','NewComponentFeatureOperation']
    with open(path_tar) as json_data:
        data_tar=json.load(json_data)
    edges_idx_tar,features_tar=format_graph_data(data_tar,bbox)
    if not path_cur:
        edges_idx_cur,features_cur=torch.zeros((0)),torch.zeros((0))
    else:
        with open(path_cur) as json_data:
            data_cur=json.load(json_data)
        edges_idx_cur,features_cur=format_graph_data(data_cur,bbox)
    graph_pair_formatted=[edges_idx_tar,features_tar,edges_idx_cur,features_cur]
    node_names=[x['id'] for x in data_tar['nodes']]
    return graph_pair_formatted,node_names,operation_names

def inference(graph_pair_formatted,model,node_names,operation_names,use_gpu=False):
    model.eval()
    num_nodes=graph_pair_formatted[1].size()[0]
    output_end_conditioned=np.zeros((num_nodes,num_nodes))
    with torch.no_grad():
        graph_pair_formatted.append(0)
        output_start,_,output_op=model(graph_pair_formatted,use_gpu=use_gpu)
        output_start=F.softmax(output_start.view(1,-1),dim=1)
        output_op=F.softmax(output_op,dim=1)
        for i in range(num_nodes):
            graph_pair_formatted[4]=i
            _,output_end,_=model(graph_pair_formatted,use_gpu=use_gpu)
            output_end=F.softmax(output_end.view(1,-1),dim=1)
            if use_gpu:
                output_end_conditioned[i,:]=output_end.data.cpu().numpy()
            else:
                output_end_conditioned[i,:]=output_end.data.numpy()
    if use_gpu:
        ps=[output_start.data.cpu().numpy()[0,:],output_end_conditioned,output_op.data.cpu().numpy()[0,:]]
    else:
        ps=[output_start.data.numpy()[0,:],output_end_conditioned,output_op.data.numpy()[0,:]]
    # enumerate all actions
    actions,probs=[],[]
    for i in range(len(node_names)):
        for j in range(len(node_names)):
            for k in range(len(operation_names)):
                actions.append([node_names[i],node_names[j],operation_names[k]])
                probs.append(ps[0][i]*ps[1][i,j]*ps[2][k])
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
    parser.add_argument('--dataset',type=str,default='data',help='Dataset name.')
    parser.add_argument('--mpn',type=str,default='gat',choices=['gat','gin'],help='Message passing network to use, can be gat or gin [default: gat]')
    args=parser.parse_args()
    args.cuda=not args.no_cuda and torch.cuda.is_available()
    # load model
    model=NodePointer(nfeat=708,nhid=256,MPN_type=args.mpn)
    model_parameters=filter(lambda p: p.requires_grad, model.parameters())
    params=sum([np.prod(p.size()) for p in model_parameters])
    print('Number params: ',params)
    checkpoint_file='../ckpt/model_%s.ckpt'%(args.mpn)
    if args.cuda:
        model.load_state_dict(torch.load(checkpoint_file))
        model.cuda()
    else:
        model.load_state_dict(
            torch.load(checkpoint_file, map_location=torch.device("cpu"))
        )
    # inference
    t1=time.time()
    for seq in ['31962_e5291336_0054']:
        # load _sequence.json, as an example
        path_seq='../%s/%s_sequence.json'%(args.dataset,seq)
        if not os.path.isfile(path_seq):
            continue
        with open(path_seq) as json_data:
            data_seq=json.load(json_data)
        path_tar='../%s/%s'%(args.dataset,data_seq['sequence'][-1]['graph'])
        bbox=data_seq['properties']['bounding_box']
        for t in range(len(data_seq['sequence'])):
            # load and format graph data from json files
            if t==0:
                path_cur=None
            else:
                path_cur='../%s/%s_%04d.json'%(args.dataset,seq,t-1)
            graph_pair_formatted,node_names,operation_names=load_graph_pair(path_tar,path_cur,bbox)
            if args.cuda:
                for j in range(4):
                    graph_pair_formatted[j]=graph_pair_formatted[j].cuda()
            # inference
            actions_sorted,probs_sorted=inference(graph_pair_formatted,model,node_names,operation_names,use_gpu=args.cuda)
            print(actions_sorted[:10])
            print(probs_sorted[:10])
    t2=time.time()
    print('%.5f seconds.'%(t2-t1))
