import pandas as pd
from typing import List, Tuple, Dict, Any

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from src.functionality.exceptions import NotFoundError


class ContentRecommender:
    def __init__(self, df: pd.DataFrame, catalog=None):
        self.df = df.copy()
        self.catalog = catalog
        self._feature_matrix = None
        self._feature_names = None
        self._build_feature_matrix()

    def _build_feature_matrix(self) -> Tuple[pd.DataFrame, List[str]]:
        if self._feature_matrix is not None:
            return self._feature_matrix, self._feature_names
        
        df_copy = self.df.copy()
        df_copy['id'] = df_copy.index
        
        if 'genres' in df_copy.columns:
            genres_exploded = df_copy.explode('genres')
            genre_dummies = pd.get_dummies(genres_exploded['genres'], prefix='genre')
            genre_dummies = genre_dummies.groupby(genres_exploded.index).sum()
            df_copy = pd.concat([df_copy, genre_dummies], axis=1)
        
        scaler = MinMaxScaler()
        if 'rating' in df_copy.columns:
            df_copy['rating_normalized'] = scaler.fit_transform(df_copy[['rating']].fillna(0))
        
        if 'release_date' in df_copy.columns:
            df_copy['year'] = pd.to_datetime(df_copy['release_date']).dt.year
            df_copy['year_normalized'] = scaler.fit_transform(df_copy[['year']].fillna(0))
        
        if 'duration' in df_copy.columns:
            df_copy['duration_normalized'] = scaler.fit_transform(df_copy[['duration']].fillna(0))
        
        if 'media_type' in df_copy.columns:
            media_type_dummies = pd.get_dummies(df_copy['media_type'], prefix='type')
            df_copy = pd.concat([df_copy, media_type_dummies], axis=1)
        
        feature_cols = [col for col in df_copy.columns if col.startswith(('genre_', 'type_')) or col.endswith('_normalized')]
        
        self._feature_matrix = df_copy[['id'] + feature_cols].set_index('id')
        self._feature_names = feature_cols
        return self._feature_matrix, self._feature_names

    def recommend_similar(self, item_id: int, top_n: int = 5, exclude_statuses: List[str] = None) -> List[Tuple[int, str, float]]:
        if exclude_statuses is None:
            exclude_statuses = ['WATCHED']
        
        features, _ = self._build_feature_matrix()
        
        if item_id not in features.index:
            raise NotFoundError(f"Item with ID {item_id} not found")
        
        if len(features) < 2:
            raise ValueError("Not enough items for recommendations")
        
        item_vector = features.loc[item_id].values.reshape(1, -1)
        all_vectors = features.values
        
        similarities = cosine_similarity(item_vector, all_vectors)[0]
        
        item_status = self.df[self.df['id'] == item_id]['status'].iloc[0] if 'id' in self.df.columns else None
        exclude_ids = self.df[self.df['status'].isin(exclude_statuses)]['id'].tolist() if 'status' in self.df.columns else []
        
        similar_items = []
        for idx, (i_id, sim) in enumerate(zip(features.index, similarities)):
            if i_id != item_id and i_id not in exclude_ids:
                title = self.df[self.df['id'] == i_id]['title'].iloc[0] if 'id' in self.df.columns else str(i_id)
                similar_items.append((i_id, title, sim))
        
        similar_items.sort(key=lambda x: x[2], reverse=True)
        return similar_items[:top_n]

    def recommend_by_status(self, status: str, top_n: int = 5, exclude_self: bool = True) -> List[Tuple[int, str, float]]:
        features, _ = self._build_feature_matrix()
        
        status_items = self.df[self.df['status'] == status]
        if status_items.empty:
            return []
        
        watched_items = self.df[self.df['status'] == 'WATCHED']
        
        if watched_items.empty:
            watched_indices = [features.index[0]]
        else:
            watched_indices = watched_items['id'].tolist()
        
        recommendations = []
        for _, item in status_items.iterrows():
            item_id = item['id'] if 'id' in item else item.name
            if item_id not in features.index:
                continue
            
            item_vector = features.loc[item_id].values.reshape(1, -1)
            
            watched_vectors = features.loc[[i for i in watched_indices if i in features.index]].values
            if len(watched_vectors) == 0:
                continue
            
            similarities = cosine_similarity(item_vector, watched_vectors)[0]
            avg_similarity = similarities.mean() if len(similarities) > 0 else 0
            
            title = item['title'] if 'title' in item else str(item_id)
            recommendations.append((item_id, title, avg_similarity))
        
        recommendations.sort(key=lambda x: x[2], reverse=True)
        return recommendations[:top_n]

    def get_item_metadata(self, item_id: int) -> Dict[str, Any]:
        if 'id' in self.df.columns:
            item = self.df[self.df['id'] == item_id]
        else:
            item = self.df.iloc[[item_id]]
        
        if item.empty:
            raise NotFoundError(f"Item with ID {item_id} not found")
        
        item = item.iloc[0]
        metadata = {
            'id': item_id,
            'title': item.get('title', 'Unknown'),
            'rating': float(item.get('rating', 0.0)) if pd.notna(item.get('rating')) else 0.0,
            'status': item.get('status', 'Unknown'),
            'genres': item.get('genres', []),
            'authors': item.get('authors', []),
            'duration': int(item.get('duration', 0)) if pd.notna(item.get('duration')) else 0
        }
        
        if 'release_date' in item and pd.notna(item['release_date']):
            metadata['release_year'] = pd.to_datetime(item['release_date']).year
        else:
            metadata['release_year'] = None
        
        return metadata


class StatusPredictor:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._features = None
        self._target = None
        self._model = None
        
    def prepare_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        df_copy = self.df.copy()
        
        df_copy['year'] = pd.to_datetime(df_copy['release_date']).dt.year
        df_copy['num_genres'] = df_copy['genres'].apply(len)
        df_copy['target'] = (df_copy['status'] == 'WATCHED').astype(int)
        
        features = ['rating', 'year', 'duration', 'num_genres']
        for col in features:
            df_copy[col] = df_copy[col].fillna(df_copy[col].median())
        
        X = df_copy[features]
        y = df_copy['target']
        
        self._features = X
        self._target = y
        return X, y

    def train_model(self, test_size: float = 0.2) -> Dict[str, float]:
        X, y = self.prepare_data()
        
        if len(X) < 5:
            return {'accuracy': 0.0, 'precision': 0.0, 'recall': 0.0, 'f1_score': 0.0}
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        self._model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._model.fit(X_train, y_train)
        
        y_pred = self._model.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0)
        }
        
        return metrics

    def predict_status(self, features: Dict[str, Any]) -> int:
        if self._model is None:
            self.train_model()
        
        feature_names = ['rating', 'year', 'duration', 'num_genres']
        X = pd.DataFrame([[
            features.get('rating', 0),
            features.get('year', 2020),
            features.get('duration', 0),
            features.get('num_genres', 1)
        ]], columns=feature_names)
        
        return int(self._model.predict(X)[0])

    def get_feature_importance(self) -> Dict[str, float]:
        if self._model is None:
            self.train_model()
        
        feature_names = ['rating', 'year', 'duration', 'num_genres']
        importance = self._model.feature_importances_
        return {name: float(imp) for name, imp in zip(feature_names, importance)}