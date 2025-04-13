from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pytrends.request import TrendReq
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt


# Initialize models and parameters
model = SentenceTransformer('all-mpnet-base-v2')
scaler = MinMaxScaler()
# Initialize Google Trends connection
pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25))

class TrendAnalyzer:
    def __init__(self, time_window=7, weights=None):
        self.time_window = time_window
        self.weights = weights or {
            'recency': 0.25,
            'velocity': 0.25,
            'volume': 0.2,
            'diversity': 0.1,
            'search_interest': 0.2
        }
    
    def get_google_trends(self, keywords, start_date, end_date):

        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        
        try:
            pytrends.build_payload(
                [f'"{k}"' for k in keywords],
                cat=0,
                timeframe=timeframe,
                geo='US',
                gprop='news'
            )
            trends_data = pytrends.interest_over_time()
            return trends_data.mean(axis=1).mean()
        except Exception as e:
            print(f"Google Trends error: {str(e)}")
            return 50  

    def calculate_trend_score(self, cluster):

        dates = [datetime.strptime(a['date'], "%Y-%m-%d") for a in cluster]
        sources = [a.get('source', 'unknown') for a in cluster]
        titles = [a['title'] for a in cluster]

        keywords = list(set([word for title in titles for word in title.split() if word.isalpha() and len(word) > 4]))
        start_date = min(dates)
        end_date = max(dates)
        

        recency = self._calculate_recency(dates)
        velocity = self._calculate_velocity(dates)
        volume = len(cluster)
        diversity = self._calculate_diversity(sources)
        search_interest = self.get_google_trends(keywords[:3], start_date, end_date) / 100


        score = sum([
            recency * self.weights['recency'],
            velocity * self.weights['velocity'],
            volume * self.weights['volume'],
            diversity * self.weights['diversity'],
            search_interest*self.weights['search_interest']
        ])
        
        return {
            'recency': recency,
            'velocity': velocity,
            'volume': volume,
            'diversity': diversity,
            'score': score,
            'search_interest':search_interest
        }

    def _calculate_recency(self, dates):
        """Fixed recency calculation using article dates as reference"""
        if not dates:
            return 0.0
        
        latest_date = max(dates)
        deltas = np.array([(latest_date - d).days for d in dates])
        
        time_window = max(self.time_window, 1)  
        deltas = np.clip(deltas, 0, None) 
        
        return np.mean(np.exp(-deltas / time_window))

    def _calculate_velocity(self, dates):
        if len(dates) < 2: return 0
        sorted_dates = sorted(dates)
        time_diffs = [(sorted_dates[i] - sorted_dates[i-1]).days 
                    for i in range(1, len(sorted_dates))]
        return np.mean(time_diffs) if time_diffs else 0

    def _calculate_diversity(self, sources):
        unique = len(set(sources))
        return unique / len(sources) if sources else 0

def hybrid_clustering(articles, eps=0.5):
    titles = [a["title"] for a in articles]
    dates = [a["date"] for a in articles]
    
    # Convert to ordinal dates
    date_ords = [datetime.strptime(d, "%Y-%m-%d").toordinal() for d in dates]
    date_feats = scaler.fit_transform(np.array(date_ords).reshape(-1, 1))
    date_feats = np.exp(-0.3 * (1 - date_feats))

    # Semantic embeddings
    text_embeds = model.encode(titles)
    text_embeds = text_embeds / np.linalg.norm(text_embeds, axis=1, keepdims=True)

    # Combine semantic and temporal info
    embeddings = np.hstack([text_embeds, 0.3 * date_feats])  # Add time weight

    # Cosine clustering
    clustering = DBSCAN(eps=eps, min_samples=2, metric='cosine')
    labels = clustering.fit_predict(embeddings)

    print("\n🧪 DBSCAN Labels:", labels)

    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity(text_embeds)
    print("\nCosine Similarity Matrix (rounded):")
    print(np.round(sims, 2))

    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(label, []).append(articles[idx])
    
    return clusters

def analyze_and_display(articles):
    clusters = hybrid_clustering(articles)
    analyzer = TrendAnalyzer()
    trends = {}
    high_trend_clusters = []
    
    def convert_numpy_types(obj):
        if isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(v) for v in obj]
        return obj

    for label, group in clusters.items():
        if label != -1 and len(group) > 1:
            try:
                cluster_id = int(label)
                cluster_data = {
                    'metrics': analyzer.calculate_trend_score(group),
                    'articles': group,
                    'cluster_id': cluster_id
                }
                converted_metrics = convert_numpy_types(cluster_data['metrics'])
                trends[label] = cluster_data
                max_score = max(t['metrics']['score'] for t in trends.values()) if trends else 1
                normalized_score = converted_metrics['score'] / max_score
                
                if normalized_score > 0.75:
                    high_trend_clusters.append({
                        'cluster_id': cluster_id,
                        'articles': [article['url'] for article in group],
                        'metrics': converted_metrics
                    })
                    
            except Exception as e:
                print(f"Error processing cluster {label}: {str(e)}")
    
    if not trends:
        print("No trending clusters found")
        return

    max_score = max(t['metrics']['score'] for t in trends.values())
    for t in trends.values():
        t['metrics']['normalized_score'] = t['metrics']['score'] / max_score

    print("\n📈 Enhanced Trend Analysis with Google Trends")
    print("=" * 65)
    for label, data in sorted(trends.items(), key=lambda x: x[1]['metrics']['normalized_score'], reverse=True):
        print(f"\nCluster {label} (Trend Score: {data['metrics']['normalized_score']:.2f})")
        print(f"  Recency: {data['metrics']['recency']:.2f}")
        print(f"  Velocity: {data['metrics']['velocity']:.2f} days/article")
        print(f"  Volume: {data['metrics']['volume']} articles")
        print(f"  Diversity: {data['metrics']['diversity']*100:.1f}%")
        print(f"  Search Interest: {data['metrics']['search_interest']*100:.1f}%")
        print("\n  Top Articles:")
        for article in data['articles']:
            print(f"   - {article['date']}: {article['title']}")
        print("-" * 65)



    return {
        'all_clusters': convert_numpy_types(trends),
        'high_trend_clusters': high_trend_clusters
    }





