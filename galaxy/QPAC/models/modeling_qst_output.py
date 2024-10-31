from dataclasses import dataclass
from typing import Optional, Tuple

import torch

from transformers.modeling_outputs import (
    BaseModelOutput,
    BaseModelOutputWithPast,
    BaseModelOutputWithPastAndCrossAttentions,
    Seq2SeqLMOutput,
    Seq2SeqModelOutput, SequenceClassifierOutputWithPast, CausalLMOutputWithPast
)


@dataclass
class QSTBaseModelOutput(BaseModelOutput):
    last_hidden_states: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    last_qst_hidden_state: torch.FloatTensor = None
    qst_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    qst_attentions: Optional[Tuple[torch.FloatTensor]] = None

@dataclass
class QSTBaseModelOutputWithPast(BaseModelOutputWithPast):
    last_hidden_states: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    last_qst_hidden_states: torch.FloatTensor = None
    qst_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    qst_attentions: Optional[Tuple[torch.FloatTensor]] = None
    past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    qst_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None

@dataclass
class SideBaseModelOutput(BaseModelOutput):
    last_hidden_state: torch.FloatTensor = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    
    side_last_hidden_state: torch.FloatTensor = None
    side_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    side_attentions: Optional[Tuple[torch.FloatTensor]] = None

@dataclass
class SideBaseModelOutputWithPastAndCrossAttentions(BaseModelOutputWithPastAndCrossAttentions):
    last_hidden_state: torch.FloatTensor = None
    past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    cross_attentions: Optional[Tuple[torch.FloatTensor]] = None
    
    side_last_hidden_state: torch.FloatTensor = None
    side_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    side_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    side_attentions: Optional[Tuple[torch.FloatTensor]] = None
    side_cross_attentions: Optional[Tuple[torch.FloatTensor]] = None


@dataclass
class SideSeq2SeqModelOutput(Seq2SeqModelOutput):
    last_hidden_state: torch.FloatTensor = None
    past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    decoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    decoder_attentions: Optional[Tuple[torch.FloatTensor]] = None
    cross_attentions: Optional[Tuple[torch.FloatTensor]] = None
    encoder_last_hidden_state: Optional[torch.FloatTensor] = None
    encoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    encoder_attentions: Optional[Tuple[torch.FloatTensor]] = None
    
    side_last_hidden_state: torch.FloatTensor = None
    side_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    side_decoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    side_decoder_attentions: Optional[Tuple[torch.FloatTensor]] = None
    side_cross_attentions: Optional[Tuple[torch.FloatTensor]] = None
    side_encoder_last_hidden_state: Optional[torch.FloatTensor] = None
    side_encoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    side_encoder_attentions: Optional[Tuple[torch.FloatTensor]] = None

@dataclass
class SideSeq2SeqLMOutput(Seq2SeqLMOutput):
    loss: Optional[torch.FloatTensor] = None
    logits: torch.FloatTensor = None
    past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    side_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    decoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    decoder_attentions: Optional[Tuple[torch.FloatTensor]] = None
    cross_attentions: Optional[Tuple[torch.FloatTensor]] = None
    encoder_last_hidden_state: Optional[torch.FloatTensor] = None
    encoder_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    encoder_attentions: Optional[Tuple[torch.FloatTensor]] = None

@dataclass
class SideSequenceClassifierOutputWithPast(SequenceClassifierOutputWithPast):
    loss: Optional[torch.FloatTensor] = None
    logits: torch.FloatTensor = None
    past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
    hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    attentions: Optional[Tuple[torch.FloatTensor]] = None
    # last_side_hidden_state: torch.FloatTensor = None
    side_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    side_attentions: Optional[Tuple[torch.FloatTensor]] = None
    side_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None

@dataclass
class QSTCausalLMOutputWithPast(CausalLMOutputWithPast):
    qst_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    qst_attentions: Optional[Tuple[torch.FloatTensor]] = None
    qst_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None

@dataclass
class QSTSequenceClassifierOutputWithPast(SequenceClassifierOutputWithPast):
    qst_hidden_states: Optional[Tuple[torch.FloatTensor]] = None
    qst_attentions: Optional[Tuple[torch.FloatTensor]] = None
    qst_past_key_values: Optional[Tuple[Tuple[torch.FloatTensor]]] = None
