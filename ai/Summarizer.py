# from datetime import datetime
# from newspaper import Article
# from langchain.chains.summarize import load_summarize_chain
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.prompts import PromptTemplate
# from langchain_community.llms import OpenAI
# import numpy as np
# from sklearn.cluster import DBSCAN
# from sentence_transformers import SentenceTransformer
# from transformers import pipeline
# import nltk  # if needed for further NLP preprocessing


# neutrality_classifier = pipeline("text-classification", model="valhalla/distilbart-mnli-12-3")
# sentiment_analyzer = pipeline("sentiment-analysis")
# fact_checker = pipeline("text2text-generation", model="google/t5_xxl_true_nli_mixture")

# # Initialize a recursive text splitter 
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)

# # prompt template 
# neutral_template = (
#     "Create a strictly factual summary that:\n"
#     "1. Lists verifiable facts first\n"
#     "2. Notes conflicting reports separately\n"
#     "3. Attributes claims to their sources\n"
#     "4. Avoids adjectives and speculation\n\n"
#     "Text: {text}\nFactual Summary:"
# )
# neutral_prompt = PromptTemplate(template=neutral_template, input_variables=["text"])

# # ------------------------------
# # Agent Classes
# # ------------------------------

# class ContentAggregationAgent:
#     """Fetches articles from a list of URLs."""
#     def fetch_articles(self, urls):
#         articles = []
#         for url in urls:
#             try:
#                 article = Article(url)
#                 article.download()
#                 article.parse()
#                 articles.append({
#                     'text': article.text,
#                     'source': url,
#                     'authors': article.authors,
#                     'publish_date': article.publish_date,
#                 })
#             except Exception as e:
#                 print(f"Error fetching {url}: {e}")
#                 continue
#         return articles

# class PerspectiveBalancingAgent:
#     """
#     Uses semantic clustering to balance perspectives.
#     The idea is to group similar articles and then limit the number
#     of articles per cluster to avoid over-representation.
#     """
#     def __init__(self):
#         self.model = SentenceTransformer('all-mpnet-base-v2')
    
#     def balance_perspectives(self, articles):
#         if not articles:
#             return []
#         texts = [a['text'] for a in articles]
#         embeddings = self.model.encode(texts)
#         clusters = DBSCAN(eps=0.6, min_samples=2).fit_predict(embeddings)
        
#         balanced_content = []
#         unique_clusters = set(clusters)
#         for cluster_id in unique_clusters:
#             if cluster_id != -1:  # Skip noise
#                 # Select up to 3 articles per perspective
#                 cluster_articles = [a for i, a in enumerate(articles) if clusters[i] == cluster_id]
#                 balanced_content.extend(cluster_articles[:3])
#         return balanced_content or articles

# class SummarizationAgent:
#     """
#     Generates an unbiased summary by extracting facts, verifying them,
#     summarizing the content via LangChain pipelines, and checking for bias.
#     """
#     def __init__(self):
#         self.chain = load_summarize_chain(
#             OpenAI(temperature=0.1),
#             chain_type="map_reduce",
#             map_prompt=neutral_prompt,
#             combine_prompt=neutral_prompt,
#             verbose=False
#         )
    
#     def fact_extraction(self, articles):
#         fact_extractor = pipeline("text2text-generation", model="pszemraj/fact-extraction")
#         all_facts = []
#         for article in articles:
#             result = fact_extractor(article['text'], max_length=512, do_sample=False)
#             extracted_text = result[0]['generated_text']
#             facts = extracted_text.split('; ')
#             all_facts.extend(facts)
#         return list(set(all_facts))
    
#     def verify_facts(self, articles, facts):
#         verified_facts = []
#         for fact in facts:
#             support = sum(1 for a in articles if fact.lower() in a['text'].lower())
#             if support / len(articles) > 0.6:  # simple majority consensus
#                 verified_facts.append(fact)
#         return verified_facts

#     def summarize(self, articles):
#         docs = text_splitter.create_documents([a['text'] for a in articles])
#         summary = self.chain.run(docs)
#         return summary

#     def generate_unbiased_summary(self, articles):
#         # 1. Fact Consensus Analysis
#         all_facts = self.fact_extraction(articles)
#         verified_facts = self.verify_facts(articles, all_facts)
#         # 2. Generate summary using LangChain
#         summary = self.summarize(articles)
#         # 3. Bias Detection
#         bias_result = neutrality_classifier(summary)
#         bias_score = bias_result[0]['score'] if bias_result else 0
#         # 4. Construct final output (include top verified facts)
#         final_summary = "Key Verified Facts:\n- " + "\n- ".join(verified_facts[:5])
#         final_summary += "\n\nSummary:\n" + summary
#         if bias_score < 0.7:
#             final_summary += "\n\n[Warning: Potential bias detected in summary]"
#         return final_summary

# # ------------------------------
# # Orchestrator Agent
# # ------------------------------

# class UnbiasedNewsSummarizationAgent:
#     """
#     Orchestrates the entire process:
#       1. Fetch articles
#       2. Balance perspectives
#       3. Generate an unbiased summary
#     """
#     def __init__(self):
#         self.content_agent = ContentAggregationAgent()
#         self.perspective_agent = PerspectiveBalancingAgent()
#         self.summarization_agent = SummarizationAgent()
    
#     def run(self, urls):
#         articles = self.content_agent.fetch_articles(urls)
#         if not articles:
#             return "No articles could be fetched."
#         balanced_articles = self.perspective_agent.balance_perspectives(articles)
#         final_summary = self.summarization_agent.generate_unbiased_summary(balanced_articles)
#         return final_summary

# # ------------------------------
# # Usage Example
# # ------------------------------

# if __name__ == "__main__":
#     # Replace these with your actual news article URLs
#     urls = [
#         "https://example.com/article1",
#         "https://example.com/article2",
#         "https://example.com/article3"
#     ]
    
#     agent = UnbiasedNewsSummarizationAgent()
#     summary = agent.run(urls)
    
#     print("Final Unbiased Summary:\n")
#     print(summary)
