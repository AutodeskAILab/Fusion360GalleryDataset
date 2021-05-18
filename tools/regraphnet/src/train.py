import argparse

if __name__=="__main__":
    # args
    parser=argparse.ArgumentParser()
    parser.add_argument('--no_cuda',action='store_true',default=False,help='Disables CUDA training.')
    parser.add_argument('--dataset',type=str,default='RegraphPerFace_05',help='Dataset name.')
    parser.add_argument('--split',type=str,default='train_test',help='Split name.')
    parser.add_argument('--seed',type=int,default=42,help='Random seed.')
    parser.add_argument('--epochs',type=int,default=100,help='Number of epochs to train.')
    parser.add_argument('--lr',type=float,default=0.0001,help='Initial learning rate.')
    parser.add_argument('--weight_decay',type=float,default=5e-4,help='Weight decay (L2 loss on parameters).')
    parser.add_argument('--hidden',type=int,default=256,help='Number of hidden units.')
    parser.add_argument('--dropout',type=float,default=0.1,help='Dropout rate.')
    parser.add_argument('--mpn',type=str,default='gcn',choices=['gcn','mlp','gat','gin'],help='Message passing network to use, can be gcn or mlp or gat or gin [default: gcn]')
    parser.add_argument('--augment',type=str,help='Directory for augmentation data.')
    parser.add_argument('--only_augment',dest='only_augment',default=False,action='store_true',help='Train with only augmented data')
    parser.add_argument('--exp_name',type=str,help='Name of the experiment. Used for the checkpoint and log files.')
    args=parser.parse_args()

    if args.mpn in ['gcn','mlp']:
        from train_vanilla import *
    else:
        from train_torch_geometric import *
    args.cuda=not args.no_cuda and torch.cuda.is_available()
    # seed
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)
    # data and model
    graph_pairs_formatted=load_dataset(args)
    if args.mpn in ['gcn','mlp']:
        model=NodePointer(nfeat=graph_pairs_formatted[0][1].size()[1],nhid=args.hidden,dropout=args.dropout,Use_GCN=(args.mpn=='gcn'))
    else:
        model=NodePointer(nfeat=graph_pairs_formatted[0][1].size()[1],nhid=args.hidden,dropout=args.dropout,MPN_type=args.mpn)
    optimizer=optim.Adam(model.parameters(),lr=args.lr)
    scheduler=ReduceLROnPlateau(optimizer,'min')
    # cuda
    if args.cuda:
        model.cuda()
        for i in range(len(graph_pairs_formatted)):
            for j in range(7):
                graph_pairs_formatted[i][j]=graph_pairs_formatted[i][j].cuda()
    # train and test
    train_test(graph_pairs_formatted,model,optimizer,scheduler,args)
