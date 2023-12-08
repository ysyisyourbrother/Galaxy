import torch

class BertConfig():
    def __init__(self):
        ''' Data Configuration '''
        # 长截短补
        self.pad_size = 32
        # 训练、验证、测试集数据路径
        self.train_path = "dataset/THUCNews/data/train.txt"
        self.dev_path = "dataset/THUCNews/data/dev.txt"
        self.test_path = "dataset/THUCNews/data/test.txt"
        self.vocab_path = "dataset/THUCNews/vocab.txt"

        ''' Training Configuration '''
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')   # 设备
        # self.device = "cpu"
        self.num_epochs = 3                                             # epoch数
        self.batch_size = 1                                           # mini-batch大小
        self.pad_size = 32                                              # 每句话处理成的长度(短填长切)
        self.learning_rate = 5e-5       
        self.class_list = [x.strip() for x in open(
            "dataset/THUCNews/data/class.txt").readlines()]                                # 类别名单
        self.num_classes = len(self.class_list)                         # 类别数

        ''' Bert Configuration '''
        # 模型参数
        self.attention_probs_dropout_prob = 0.1
        self.directionality = "bidi"
        self.hidden_act = "gelu"
        self.hidden_dropout_prob = 0.1
        self.initializer_range = 0.02
        self.layer_norm_eps = 1e-12
        self.max_position_embeddings = 512
        self.model_type = "bert"
        self.pad_token_id = 0

        # 修改模型大小
        self.hidden_size = 768
        self.intermediate_size = 4*self.hidden_size                # MLP层两个dense层中间的intermediate state大小
        self.num_attention_heads = 12
        self.num_hidden_layers = 1 
        self.att_head_size = int(self.hidden_size/self.num_attention_heads)

        # 词表
        self.type_vocab_size = 2
        self.vocab_size = 21128

        ''' Distributed Configuration '''
        self.stage = 1 
        self.total_stage = 2 
        self.next_rank = None
        self.pre_rank = 0
        # self.init_method = "tcp://192.168.124.4:23000"                         # torch.dist.init_process_group中使用的master device    
        self.init_method = "tcp://127.0.0.1:23000"                         # torch.dist.init_process_group中使用的master device    
        self.distributed_backend = "gloo"
        self.num_microbatches = 4
        self.num_hidden_layers = 1                  # 覆盖模型参数 
        self.pre_process = False
        self.post_process = True
        
        # lora
        self.use_lora = False
        self.lora_att_dim = 4
        self.lora_alpha = 32
        self.lora_dropout = 0.1
        self.fan_in_fan_out = True
        self.merge_weights = False


config = BertConfig()