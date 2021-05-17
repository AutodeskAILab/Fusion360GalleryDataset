import os
import argparse

if __name__=="__main__":
    # args
    parser=argparse.ArgumentParser()
    parser.add_argument('--no_cuda',action='store_true',default=True,help='Disables CUDA training.')
    parser.add_argument('--dataset',type=str,default='data',help='Dataset name.')
    parser.add_argument('--mpn',type=str,default='gcn',choices=['gcn','mlp','gat','gin'],help='Message passing network to use, can be gcn or mlp or gat or gin [default: gcn]')
    parser.add_argument('--augment',dest='augment',default=False,action='store_true',help='Use the checkpoint trained with additional augmented data')
    parser.add_argument('--only_augment',dest='only_augment',default=False,action='store_true',help='Use the checkpoint trained on only augmented data')
    args=parser.parse_args()

    checkpoint_name=f'model_{args.mpn}'
    if args.augment:
        checkpoint_name+='_aug'
    elif args.only_augment:
        checkpoint_name+='_syn' 
    checkpoint_file=f'../ckpt/{checkpoint_name}.ckpt'
    if not os.path.isfile(checkpoint_file):
        print(f'Checkpoint file not found: {checkpoint_file}')
        exit()
    else:
        print(f'Using checkpoint file: {checkpoint_file}')

    if args.mpn in ['gcn','mlp']:
        from inference_vanilla import *
        args.cuda=not args.no_cuda and torch.cuda.is_available()
        # load model
        model=NodePointer(nfeat=708,nhid=256,Use_GCN=(args.mpn=='gcn'))
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
    else:
        from inference_torch_geometric import *
        args.cuda=not args.no_cuda and torch.cuda.is_available()
        # load model
        model=NodePointer(nfeat=708,nhid=256,MPN_type=args.mpn)
        model_parameters=filter(lambda p: p.requires_grad, model.parameters())
        params=sum([np.prod(p.size()) for p in model_parameters])
        print('Number params: ',params)
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
