import sys, os, copy
import numpy as np
import torch
import torch_pruning as tp
import transformers

import functools

def round_pruning_amount(total_parameters, n_to_prune, round_to):
    """round the parameter amount after pruning to an integer multiple of `round_to`.
    """
    n_remain = round_to*max(int(total_parameters - n_to_prune)//round_to, 1)
    return max(total_parameters - n_remain, 0)

# Load BertModel from https://github.com/huggingface/transformers


def pruning_v1(model, reduction_factor):

    inputs_dict = {
        "input_ids": torch.randint(0, model.shared.weight.shape[0], (32, 128)), 
        "decoder_input_ids": torch.ones(32, 1, dtype=torch.long) * model.config.decoder_start_token_id
    }

    # Build dependency graph
    DG = tp.DependencyGraph()

    DG.register_customized_layer(
        transformers.models.t5.modeling_t5.T5LayerNorm, 
        in_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of input tensor
        out_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of output tensor
        get_in_ch_fn=lambda l: None,  # estimate the n_channel of layer input. Return None if the layer does not change tensor shape.
        get_out_ch_fn=lambda l: None
    ) # estimate the n_channel of layer output. Return None if the layer does not change tensor shape.


    DG.build_dependency(model, example_inputs = inputs_dict, pruning_dim = -1) # Note to set pruning_dim to -1 to prune BertModel on hidden_states.

    prune_val = 1 - 1 / reduction_factor
    # get a pruning plan by pruning from word embedding
    strategy = tp.strategy.L1Strategy() 
    pruning_idxs = strategy(model.shared.weight.T, amount=prune_val) # Transpose the weight matrix to [num_embeddings, embedding_dim]
    pruning_plan = DG.get_pruning_plan( model.shared, tp.prune_embedding, idxs=pruning_idxs )

    # execute the plan (prune the model) and save the model
    pruning_plan.exec()

    for sub_model in ["encoder", "decoder"]:
        for i in range(12):
            # self attention
            q_name = f"model.{sub_model}.block[{i}].layer[0].SelfAttention.q"
            k_name = f"model.{sub_model}.block[{i}].layer[0].SelfAttention.k"
            v_name = f"model.{sub_model}.block[{i}].layer[0].SelfAttention.v"
            o_name = f"model.{sub_model}.block[{i}].layer[0].SelfAttention.o"

            q_weights = q_name + ".weight"
            k_weights = k_name + ".weight"
            v_weights = v_name + ".weight"
            o_weights = o_name + ".weight.T"

            weights = eval(q_weights) * eval(k_weights) * eval(v_weights) * eval(o_weights)

            pruning_idxs = strategy(weights, amount=prune_val)

            pruning_plan = DG.get_pruning_plan( eval(v_name), tp.prune_linear, idxs=pruning_idxs )

            pruning_plan.exec()

            # cross attention
            if sub_model == "decoder":
                q_name = f"model.{sub_model}.block[{i}].layer[1].EncDecAttention.q"
                k_name = f"model.{sub_model}.block[{i}].layer[1].EncDecAttention.k"
                v_name = f"model.{sub_model}.block[{i}].layer[1].EncDecAttention.v"
                o_name = f"model.{sub_model}.block[{i}].layer[1].EncDecAttention.o"

                q_weights = q_name + ".weight"
                k_weights = k_name + ".weight"
                v_weights = v_name + ".weight"
                o_weights = o_name + ".weight.T"

                weights = eval(q_weights) * eval(k_weights) * eval(v_weights) * eval(o_weights)

                pruning_idxs = strategy(weights, amount=prune_val)

                pruning_plan = DG.get_pruning_plan( eval(v_name), tp.prune_linear, idxs=pruning_idxs )

                pruning_plan.exec()

            # feed forward
            wi_name = f"model.{sub_model}.block[{i}].layer[-1].DenseReluDense.wi"
            wo_name = f"model.{sub_model}.block[{i}].layer[-1].DenseReluDense.wo"

            wi_weights = wi_name + ".weight"
            wo_weights = wo_name + ".weight.T"

            weights = eval(wi_weights) * eval(wo_weights)

            pruning_idxs = strategy(weights, amount=prune_val)

            pruning_plan = DG.get_pruning_plan( eval(wi_name), tp.prune_linear, idxs=pruning_idxs )

            # execute the plan (prune the model) and save the model
            pruning_plan.exec()

    return model.state_dict()


def select_weights(weights, idxs):
    num_features = len(weights)
    keep_idxs = list(set(range(num_features)) - set(idxs))

    return weights[keep_idxs]


def pruning_bottleneck(model, reduction_factor, importance_measure=None, version=2, num_heads=12, iterations=2):

    inputs_dict = {
        "input_ids": torch.randint(0, model.shared.weight.shape[0], (32, 128)), 
        "decoder_input_ids": torch.ones(32, 1, dtype=torch.long) * model.config.decoder_start_token_id
    }

    # Build dependency graph
    DG = tp.DependencyGraph()

    DG.register_customized_layer(
        transformers.models.t5.modeling_t5.T5LayerNorm, 
        in_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of input tensor
        out_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of output tensor
        get_in_ch_fn=lambda l: None,  # estimate the n_channel of layer input. Return None if the layer does not change tensor shape.
        get_out_ch_fn=lambda l: None
    ) # estimate the n_channel of layer output. Return None if the layer does not change tensor shape.


    DG.build_dependency(model, example_inputs = inputs_dict, pruning_dim = -1) # Note to set pruning_dim to -1 to prune BertModel on hidden_states.

    if version in [2, 5]:
        strategy_for_attn = tp.strategy.L1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
    elif version == 3:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
        num_heads = num_heads
        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
    elif version == 4:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.AttnL1Strategy()

        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
        strategy_for_others = functools.partial(strategy_for_attn, num_heads=num_heads)

    prune_vals = np.linspace(0, 1 - 1 / reduction_factor, iterations)
    # print(np.rint(prune_vals * 768))
    keep_vals = 1 - prune_vals
    keep_vals_now = keep_vals[1:]
    keep_vals_pre = keep_vals[:-1] 
    prune_vals = (keep_vals_pre - keep_vals_now) / keep_vals_pre

    prune_vals = prune_vals.tolist()
    
    state_dict = model.state_dict()
    if importance_measure is None:
        importance_measure = copy.deepcopy(state_dict)

    ordered_target_layers = []
    sub_model = "encoder"

    ordered_target_layers.append(
        [f"{sub_model}.block.0.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
    )

    for i in range(model.config.num_layers):
        # ordered_target_layers.append(
        #     [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
        # )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.1.DenseReluDense.{n}.weight" for n in ["wi", "wo"]])

    sub_model = "decoder"

    ordered_target_layers.append(
        [f"{sub_model}.block.0.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
        )
    
    for i in range(model.config.num_decoder_layers):
        # ordered_target_layers.append(
        #     [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
        #     )
        ordered_target_layers.append(
            [f"{sub_model}.block.{i}.layer.1.EncDecAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
            )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.2.DenseReluDense.{n}.weight" for n in ["wi", "wo"]])

    module_mapping = {}

    sub_model = "encoder"
    for i in range(model.config.num_layers):
        for n in ["q", "k", "v", "o"]:
            module_mapping[f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[0].SelfAttention.{n}.weight"

        for n in ["wi", "wo"]:
            module_mapping[f"{sub_model}.block.{i}.layer.1.DenseReluDense.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[1].DenseReluDense.{n}.weight"

    sub_model = "decoder"

    for i in range(model.config.num_decoder_layers):
        for n in ["q", "k", "v", "o"]:
            module_mapping[f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[0].SelfAttention.{n}.weight"
            module_mapping[f"{sub_model}.block.{i}.layer.1.EncDecAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[1].EncDecAttention.{n}.weight"

        for n in ["wi", "wo"]:
            module_mapping[f"{sub_model}.block.{i}.layer.2.DenseReluDense.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[2].DenseReluDense.{n}.weight"
    
    for prune_val in prune_vals:
        for layer in ordered_target_layers:
            is_attn = any(["Attention" in sub_layer for sub_layer in layer])

            if is_attn:
                strategy = strategy_for_attn
            else:
                strategy = strategy_for_others
            
            # importances = [importance_measure[sub_layer] for sub_layer in layer]

            prod_imp = 1
            for sub_layer in layer:
                if "Attention.o" in sub_layer or "DenseReluDense.wo" in sub_layer:
                    prod_imp *= importance_measure[sub_layer].T
                else:
                    prod_imp *= importance_measure[sub_layer]

            pruning_idxs = strategy(weights=prod_imp, amount=prune_val)

            module = module_mapping[layer[0]]
            module = ["model"] + module.split(".")[:-1]

            module = eval(".".join(module))

            pruning_plan = DG.get_pruning_plan(module, tp.prune_linear, idxs=pruning_idxs)

            # execute the plan (prune the model) and save the model
            pruning_plan.exec()

            print(module, module.weight.shape)

    return model.state_dict()


def pruning_with_residual(model, reduction_factor, importance_measure=None, version=2, num_heads=12, iterations=2):

    inputs_dict = {
        "input_ids": torch.randint(0, model.shared.weight.shape[0], (32, 128)), 
        "decoder_input_ids": torch.ones(32, 1, dtype=torch.long) * model.config.decoder_start_token_id
    }

    # Build dependency graph
    DG = tp.DependencyGraph()

    DG.register_customized_layer(
        transformers.models.t5.modeling_t5.T5LayerNorm, 
        in_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of input tensor
        out_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of output tensor
        get_in_ch_fn=lambda l: None,  # estimate the n_channel of layer input. Return None if the layer does not change tensor shape.
        get_out_ch_fn=lambda l: None
    ) # estimate the n_channel of layer output. Return None if the layer does not change tensor shape.


    DG.build_dependency(model, example_inputs = inputs_dict, pruning_dim = -1) # Note to set pruning_dim to -1 to prune BertModel on hidden_states.

    if version in [2, 5]:
        strategy_for_attn = tp.strategy.L1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
    elif version == 3:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
        num_heads = num_heads
        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
    elif version == 4:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.AttnL1Strategy()

        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
        strategy_for_others = functools.partial(strategy_for_attn, num_heads=num_heads)

    prune_vals = np.linspace(0, 1 - 1 / reduction_factor, iterations)
    # print(np.rint(prune_vals * 768))
    keep_vals = 1 - prune_vals
    keep_vals_now = keep_vals[1:]
    keep_vals_pre = keep_vals[:-1] 
    prune_vals = (keep_vals_pre - keep_vals_now) / keep_vals_pre

    prune_vals = prune_vals.tolist()
    
    state_dict = model.state_dict()
    if importance_measure is None:
        importance_measure = copy.deepcopy(state_dict)

    ordered_target_layers = []
    sub_model = "encoder"
    
    ordered_target_layers.append(
        [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"] for i in range(12)]
    )

    for i in range(model.config.num_layers):
        # ordered_target_layers.append(
        #     [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
        # )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.1.DenseReluDense.{n}.weight" for n in ["wi", "wo"]])

    sub_model = "decoder"

    ordered_target_layers.append(
        [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"] for i in range(12)]
        )
    
    for i in range(model.config.num_decoder_layers):
        # ordered_target_layers.append(
        #     [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
        #     )
        ordered_target_layers.append(
            [f"{sub_model}.block.{i}.layer.1.EncDecAttention.{n}.weight" for n in ["q", "k", "v", "o"]]
            )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.2.DenseReluDense.{n}.weight" for n in ["wi", "wo"]])

    module_mapping = {}

    sub_model = "encoder"
    for i in range(model.config.num_layers):
        for n in ["q", "k", "v", "o"]:
            module_mapping[f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[0].SelfAttention.{n}.weight"

        for n in ["wi", "wo"]:
            module_mapping[f"{sub_model}.block.{i}.layer.1.DenseReluDense.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[1].DenseReluDense.{n}.weight"

    sub_model = "decoder"

    for i in range(model.config.num_decoder_layers):
        for n in ["q", "k", "v", "o"]:
            module_mapping[f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[0].SelfAttention.{n}.weight"
            module_mapping[f"{sub_model}.block.{i}.layer.1.EncDecAttention.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[1].EncDecAttention.{n}.weight"

        for n in ["wi", "wo"]:
            module_mapping[f"{sub_model}.block.{i}.layer.2.DenseReluDense.{n}.weight"] = \
                f"{sub_model}.block[{i}].layer[2].DenseReluDense.{n}.weight"
    
    for prune_val in prune_vals:
        pruning_idxs = strategy_for_others(importance_measure["shared.weight"].T, amount=prune_val) # Transpose the weight matrix to [num_embeddings, embedding_dim]
        pruning_plan = DG.get_pruning_plan(model.shared, tp.prune_embedding, idxs=pruning_idxs)

        pruning_plan.exec()

        for layer in ordered_target_layers:
            is_attn = any(["Attention" in sub_layer for sub_layer in layer])

            if is_attn:
                strategy = strategy_for_attn
            else:
                strategy = strategy_for_others
            
            # importances = [importance_measure[sub_layer] for sub_layer in layer]

            overall_imp = 1
            for sub_layer in layer:
                if "Attention.o" in sub_layer or "DenseReluDense.wo" in sub_layer:
                    overall_imp += torch.log(importance_measure[sub_layer].T)
                else:
                    overall_imp += torch.log(importance_measure[sub_layer])

            pruning_idxs = strategy(weights=overall_imp, amount=prune_val)

            module = module_mapping[layer[0]]
            module = ["model"] + module.split(".")[:-1]

            module = eval(".".join(module))

            pruning_plan = DG.get_pruning_plan(module, tp.prune_linear, idxs=pruning_idxs)

            # execute the plan (prune the model) and save the model
            pruning_plan.exec()

            # print(module, module.weight.shape)

    return model.state_dict()


def pruning_without_residual(model, reduction_factor, importance_measure=None, version=2, num_heads=12, iterations=2):
    inputs_dict = {
        "input_ids": torch.randint(0, model.shared.weight.shape[0], (32, 128)), 
        "decoder_input_ids": torch.ones(32, 1, dtype=torch.long) * model.config.decoder_start_token_id
    }

    # Build dependency graph
    DG = tp.DependencyGraph()
    
    # register custom pruning method for t5 layernorm
    DG.register_customized_layer(
        transformers.models.t5.modeling_t5.T5LayerNorm, 
        in_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of input tensor
        out_ch_pruning_fn=tp.prune_t5layernorm, # A function to prune channels/dimensions of output tensor
        get_in_ch_fn=lambda l: None,  # estimate the n_channel of layer input. Return None if the layer does not change tensor shape.
        get_out_ch_fn=lambda l: None
    ) # estimate the n_channel of layer output. Return None if the layer does not change tensor shape.

    DG.build_dependency(model, example_inputs = inputs_dict, pruning_dim = -1) # Note to set pruning_dim to -1 to prune BertModel on hidden_states.

    # get a pruning plan by pruning from word embedding

    if version in [2, 5]:
        strategy_for_attn = tp.strategy.L1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
    elif version == 3:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.L1Strategy()
        num_heads = num_heads
        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
    elif version == 4:
        strategy_for_attn = tp.strategy.AttnL1Strategy()
        strategy_for_others = tp.strategy.AttnL1Strategy()

        strategy_for_attn = functools.partial(strategy_for_attn, num_heads=num_heads)
        strategy_for_others = functools.partial(strategy_for_attn, num_heads=num_heads)

    if version in [2, 3, 4]:
        prune_vals = [1 - 1 / reduction_factor]
    elif version in [5]:
        prune_vals = np.linspace(0, 1 - 1 / reduction_factor, iterations)
        # print(np.rint(prune_vals * 768))
        keep_vals = 1 - prune_vals
        keep_vals_now = keep_vals[1:]
        keep_vals_pre = keep_vals[:-1] 
        prune_vals = (keep_vals_pre - keep_vals_now) / keep_vals_pre

        prune_vals = prune_vals.tolist()
        # round_pruning_amount(n, n_to_prune, round_to)

    state_dict = model.state_dict()
    if importance_measure is None:
        importance_measure = copy.deepcopy(state_dict)

    # construct ordered layers to process
    ordered_target_layers = ["shared.weight", "encoder.embed_tokens.weight", "encoder.block.0.layer.0.SelfAttention.relative_attention_bias.weight"]

    sub_model = "encoder"
    for i in range(model.config.num_layers):
        ordered_target_layers.append(f"{sub_model}.block.{i}.layer.0.layer_norm.weight")
        ordered_target_layers.append(
            [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v"]]
            )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.0.SelfAttention.o.weight"])
        ordered_target_layers.append(f"{sub_model}.block.{i}.layer.1.layer_norm.weight")
    
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.1.DenseReluDense.wi.weight"])
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.1.DenseReluDense.wo.weight"])

    ordered_target_layers.append(f"{sub_model}.final_layer_norm.weight")
    ordered_target_layers.append(f"decoder.embed_tokens.weight")
    ordered_target_layers.append(f"decoder.block.0.layer.0.SelfAttention.relative_attention_bias.weight")

    sub_model = "decoder"
    for i in range(model.config.num_decoder_layers):
        ordered_target_layers.append(f"{sub_model}.block.{i}.layer.0.layer_norm.weight")
        ordered_target_layers.append(
            [f"{sub_model}.block.{i}.layer.0.SelfAttention.{n}.weight" for n in ["q", "k", "v"]]
            )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.0.SelfAttention.o.weight"])
        ordered_target_layers.append(f"{sub_model}.block.{i}.layer.1.layer_norm.weight")
        ordered_target_layers.append(
            [f"{sub_model}.block.{i}.layer.1.EncDecAttention.{n}.weight" for n in ["q", "k", "v"]]
            )
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.1.EncDecAttention.o.weight"])
        ordered_target_layers.append(f"{sub_model}.block.{i}.layer.2.layer_norm.weight")
   
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.2.DenseReluDense.wi.weight"])
        ordered_target_layers.append([f"{sub_model}.block.{i}.layer.2.DenseReluDense.wo.weight"])

    ordered_target_layers.append(f"{sub_model}.final_layer_norm.weight")
    ordered_target_layers.append(f"lm_head.weight")
    
    for prune_val in prune_vals:
        new_state_dict = {}
        for layer in ordered_target_layers:
            if isinstance(layer, list):
                # the most common case
                # will prune the weights according to previous prune idx and select next prune idx

                is_attn = any(["Attention" in sub_layer for sub_layer in layer])

                if is_attn:
                    strategy = strategy_for_attn
                else:
                    strategy = strategy_for_others
               
                weights = [state_dict[sub_layer] for sub_layer in layer]
                importances = [importance_measure[sub_layer] for sub_layer in layer]

                # prune according to previous idx
                weights = [select_weights(w.T, pruning_idxs).T for w in weights]
                importances = [select_weights(imp.T, pruning_idxs).T for imp in importances]

                prod_imp = 1
                for imp in importances:
                    prod_imp *= imp

                pruning_idxs = strategy(weights=prod_imp, amount=prune_val)

                weights = [select_weights(w, pruning_idxs) for w in weights]
                importances = [select_weights(imp, pruning_idxs) for imp in importances]

                for l, w in zip(layer, weights):
                    new_state_dict[l] = w

                # update importance measure
                for l, imp in zip(layer, importances):
                    importance_measure[l] = imp

            elif "shared.weight" in layer:
                # the first layer
                # will only select next prune idx
                # and direct copy the same weights
                importance = importance_measure[layer]
                weights = state_dict[layer]
                pruning_idxs = strategy_for_others(weights=importance.T, amount=prune_val)

                weights = select_weights(weights.T, pruning_idxs).T
                importance = select_weights(importance.T, pruning_idxs).T

                new_state_dict[layer] = weights
                importance_measure[layer] = importance
            
            elif "layer_norm" in layer:
                # will only prune the weights according to previous prune idx
                weights = state_dict[layer]
                weights = select_weights(weights, pruning_idxs)

                importance = importance_measure[layer]
                importance = select_weights(importance, pruning_idxs)
                
                new_state_dict[layer] = weights
                importance_measure[layer] = importance
                
            else:
                # do nothing, just copy the same weight
                new_state_dict[layer] = state_dict[layer]

        # j = 0
        # for k, v in new_state_dict.items():
        #     print(v.shape)

        #     if j > 4:
        #         break
        #     j += 1

        state_dict = new_state_dict

    return new_state_dict


def pruning_T5ForConditionalGeneration(model, reduction_factor, importance_measure=None):
    return pruning_without_residual(model, reduction_factor, importance_measure=importance_measure, version=2)


def pruning_v3(model, reduction_factor, importance_measure=None):
    return pruning_without_residual(model, reduction_factor, importance_measure=importance_measure, version=3, num_heads=12)


def pruning_v4(model, reduction_factor, num_heads, importance_measure=None):
    return pruning_without_residual(model, reduction_factor, importance_measure=importance_measure, version=4, num_heads=num_heads)


def pruning_v5(model, reduction_factor, importance_measure=None, iterations=11):
    return pruning_without_residual(model, reduction_factor, importance_measure=importance_measure, version=5, iterations=iterations)
