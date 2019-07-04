from flair.data import Sentence
from flair.embeddings import BertEmbeddings, StackedEmbeddings
from flair.embeddings import FlairEmbeddings
from flair.models   import LanguageModel
from flair.embeddings import ELMoEmbeddings

embedding = BertEmbeddings('bert-base-chinese')
# lm=FlairEmbeddings().lm
# lm.calculate_perplexity( NLPP)
# model=embedding.model
# LanguageModel.calculate_perplexity()
# StackedEmbeddings
s='习近平指出，要紧紧扭住战争和作战问题推进军事理论创新，构建具有我军特色、符合现代战争规律的先进作战理论体系，不断开辟当代中国马克思主义军事理论发展新境界。要打通从实践到理论、再从理论到实践的闭环回路，让军事理论研究植根实践沃土、接受实践检验，实现理论和实践良性互动。'
# s='i am a teacher.'
sentence=Sentence(s)
embedding.embed(sentence)
print(sentence)