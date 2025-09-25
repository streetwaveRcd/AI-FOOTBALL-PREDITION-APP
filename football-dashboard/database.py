import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

class FootballDatabase:
    """Database handler for storing predictions and match results."""
    
    def __init__(self, db_path: str = 'football_predictions.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create predictions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER UNIQUE NOT NULL,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    home_team_name TEXT NOT NULL,
                    away_team_name TEXT NOT NULL,
                    competition_id INTEGER,
                    competition_name TEXT,
                    match_date TEXT NOT NULL,
                    predicted_outcome TEXT NOT NULL,  -- HOME_WIN, AWAY_WIN, DRAW
                    predicted_team TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    home_win_prob REAL,
                    draw_prob REAL,
                    away_win_prob REAL,
                    ht_home_win_ft_lose_prob REAL,  -- Half-time home win, full-time lose
                    ht_away_win_ft_lose_prob REAL,  -- Half-time away win, full-time lose
                    reasoning TEXT,
                    prediction_method TEXT DEFAULT 'basic',  -- basic, gpt, hybrid
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    team_stats TEXT  -- JSON string of team statistics
                )
            ''')
            
            # Create match results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS match_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER UNIQUE NOT NULL,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    home_team_name TEXT NOT NULL,
                    away_team_name TEXT NOT NULL,
                    competition_id INTEGER,
                    competition_name TEXT,
                    match_date TEXT NOT NULL,
                    home_score INTEGER,
                    away_score INTEGER,
                    ht_home_score INTEGER,  -- Half-time scores
                    ht_away_score INTEGER,
                    actual_outcome TEXT,  -- HOME_WIN, AWAY_WIN, DRAW
                    ht_outcome TEXT,  -- Half-time outcome
                    ht_win_ft_lose_outcome TEXT,  -- HT_HOME_WIN_FT_LOSE, HT_AWAY_WIN_FT_LOSE, NONE
                    match_status TEXT DEFAULT 'FINISHED',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create prediction accuracy tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prediction_accuracy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER,
                    match_id INTEGER,
                    was_correct BOOLEAN NOT NULL,
                    confidence_bucket TEXT,  -- LOW, MEDIUM, HIGH, ELITE
                    prediction_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id) REFERENCES predictions (id),
                    FOREIGN KEY (match_id) REFERENCES match_results (match_id)
                )
            ''')
            
            # Create prediction batches table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prediction_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_name TEXT NOT NULL,
                    batch_date TEXT NOT NULL,
                    description TEXT,
                    total_predictions INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Update predictions table to support batch association (handle gracefully if column exists)
            try:
                cursor.execute('''
                    ALTER TABLE predictions ADD COLUMN batch_id INTEGER DEFAULT NULL
                ''')
            except sqlite3.OperationalError:
                # Column already exists, ignore
                pass
            
            conn.commit()
    
    def save_prediction(self, match_data: Dict, prediction_data: Dict) -> bool:
        """Save a prediction to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Extract match information
                match_id = match_data.get('id')
                home_team = match_data.get('homeTeam', {})
                away_team = match_data.get('awayTeam', {})
                competition = match_data.get('competition', {})
                
                # Prepare team stats as JSON
                team_stats_json = json.dumps(prediction_data.get('team_stats', {}))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO predictions (
                        match_id, home_team_id, away_team_id, home_team_name, away_team_name,
                        competition_id, competition_name, match_date, predicted_outcome,
                        predicted_team, confidence, home_win_prob, draw_prob, away_win_prob,
                        ht_home_win_ft_lose_prob, ht_away_win_ft_lose_prob, reasoning, team_stats
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match_id,
                    home_team.get('id'),
                    away_team.get('id'),
                    home_team.get('name', 'Unknown'),
                    away_team.get('name', 'Unknown'),
                    competition.get('id'),
                    competition.get('name', 'Unknown'),
                    match_data.get('utcDate'),
                    prediction_data.get('prediction'),
                    prediction_data.get('predicted_team'),
                    prediction_data.get('confidence'),
                    prediction_data.get('probabilities', {}).get('home_win'),
                    prediction_data.get('probabilities', {}).get('draw'),
                    prediction_data.get('probabilities', {}).get('away_win'),
                    prediction_data.get('probabilities', {}).get('ht_home_win_ft_lose'),
                    prediction_data.get('probabilities', {}).get('ht_away_win_ft_lose'),
                    prediction_data.get('reasoning'),
                    team_stats_json
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving prediction: {e}")
            return False
    
    def save_match_result(self, match_data: Dict) -> bool:
        """Save a match result to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Only save if match is finished
                if match_data.get('status') != 'FINISHED':
                    return False
                
                match_id = match_data.get('id')
                home_team = match_data.get('homeTeam', {})
                away_team = match_data.get('awayTeam', {})
                competition = match_data.get('competition', {})
                score = match_data.get('score', {}).get('fullTime', {})
                ht_score = match_data.get('score', {}).get('halfTime', {})
                
                home_score = score.get('home')
                away_score = score.get('away')
                ht_home_score = ht_score.get('home')
                ht_away_score = ht_score.get('away')
                
                # Determine actual outcome
                actual_outcome = None
                ht_outcome = None
                ht_win_ft_lose_outcome = 'NONE'
                
                if home_score is not None and away_score is not None:
                    if home_score > away_score:
                        actual_outcome = 'HOME_WIN'
                    elif away_score > home_score:
                        actual_outcome = 'AWAY_WIN'
                    else:
                        actual_outcome = 'DRAW'
                
                # Determine half-time outcome
                if ht_home_score is not None and ht_away_score is not None:
                    if ht_home_score > ht_away_score:
                        ht_outcome = 'HOME_WIN'
                        # Check if home was winning at HT but lost at FT
                        if actual_outcome == 'AWAY_WIN':
                            ht_win_ft_lose_outcome = 'HT_HOME_WIN_FT_LOSE'
                    elif ht_away_score > ht_home_score:
                        ht_outcome = 'AWAY_WIN'
                        # Check if away was winning at HT but lost at FT
                        if actual_outcome == 'HOME_WIN':
                            ht_win_ft_lose_outcome = 'HT_AWAY_WIN_FT_LOSE'
                    else:
                        ht_outcome = 'DRAW'
                
                cursor.execute('''
                    INSERT OR REPLACE INTO match_results (
                        match_id, home_team_id, away_team_id, home_team_name, away_team_name,
                        competition_id, competition_name, match_date, home_score, away_score,
                        ht_home_score, ht_away_score, actual_outcome, ht_outcome, ht_win_ft_lose_outcome,
                        match_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match_id,
                    home_team.get('id'),
                    away_team.get('id'),
                    home_team.get('name', 'Unknown'),
                    away_team.get('name', 'Unknown'),
                    competition.get('id'),
                    competition.get('name', 'Unknown'),
                    match_data.get('utcDate'),
                    home_score,
                    away_score,
                    ht_home_score,
                    ht_away_score,
                    actual_outcome,
                    ht_outcome,
                    ht_win_ft_lose_outcome,
                    match_data.get('status')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving match result: {e}")
            return False
    
    def get_prediction_comparisons(self, limit: int = 100) -> List[Dict]:
        """Get predictions with their corresponding match results for comparison."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        p.match_id,
                        p.home_team_name,
                        p.away_team_name,
                        p.competition_name,
                        p.match_date,
                        p.predicted_outcome,
                        p.predicted_team,
                        p.confidence,
                        p.home_win_prob,
                        p.draw_prob,
                        p.away_win_prob,
                        p.reasoning,
                        p.team_stats,
                        r.home_score,
                        r.away_score,
                        r.actual_outcome,
                        (p.predicted_outcome = r.actual_outcome) as was_correct
                    FROM predictions p
                    LEFT JOIN match_results r ON p.match_id = r.match_id
                    WHERE r.actual_outcome IS NOT NULL
                    ORDER BY p.match_date DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                
                comparisons = []
                for row in rows:
                    team_stats = {}
                    try:
                        team_stats = json.loads(row[12]) if row[12] else {}
                    except json.JSONDecodeError:
                        team_stats = {}
                    
                    comparison = {
                        'match_id': row[0],
                        'home_team': row[1],
                        'away_team': row[2],
                        'competition': row[3],
                        'match_date': row[4],
                        'prediction': {
                            'outcome': row[5],
                            'predicted_team': row[6],
                            'confidence': row[7],
                            'probabilities': {
                                'home_win': row[8],
                                'draw': row[9],
                                'away_win': row[10]
                            },
                            'reasoning': row[11],
                            'team_stats': team_stats
                        },
                        'result': {
                            'home_score': row[13],
                            'away_score': row[14],
                            'actual_outcome': row[15]
                        },
                        'was_correct': bool(row[16]) if row[16] is not None else False
                    }
                    comparisons.append(comparison)
                
                return comparisons
                
        except Exception as e:
            print(f"Error getting prediction comparisons: {e}")
            return []
    
    def get_prediction_statistics(self) -> Dict:
        """Get overall prediction accuracy statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Overall accuracy
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) as correct_predictions
                    FROM predictions p
                    JOIN match_results r ON p.match_id = r.match_id
                    WHERE r.actual_outcome IS NOT NULL
                ''')
                
                overall_row = cursor.fetchone()
                total_predictions = overall_row[0] if overall_row else 0
                correct_predictions = overall_row[1] if overall_row else 0
                overall_accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
                
                # Accuracy by confidence level
                cursor.execute('''
                    SELECT 
                        CASE 
                            WHEN p.confidence >= 80 THEN 'ELITE'
                            WHEN p.confidence >= 70 THEN 'HIGH'
                            WHEN p.confidence >= 50 THEN 'MEDIUM'
                            ELSE 'LOW'
                        END as confidence_bucket,
                        COUNT(*) as total,
                        SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) as correct,
                        AVG(p.confidence) as avg_confidence
                    FROM predictions p
                    JOIN match_results r ON p.match_id = r.match_id
                    WHERE r.actual_outcome IS NOT NULL
                    GROUP BY confidence_bucket
                    ORDER BY avg_confidence DESC
                ''')
                
                confidence_stats = []
                for row in cursor.fetchall():
                    bucket_accuracy = (row[2] / row[1] * 100) if row[1] > 0 else 0
                    confidence_stats.append({
                        'confidence_bucket': row[0],
                        'total_predictions': row[1],
                        'correct_predictions': row[2],
                        'accuracy': round(bucket_accuracy, 1),
                        'avg_confidence': round(row[3], 1)
                    })
                
                # Accuracy by prediction type
                cursor.execute('''
                    SELECT 
                        p.predicted_outcome,
                        COUNT(*) as total,
                        SUM(CASE WHEN p.predicted_outcome = r.actual_outcome THEN 1 ELSE 0 END) as correct
                    FROM predictions p
                    JOIN match_results r ON p.match_id = r.match_id
                    WHERE r.actual_outcome IS NOT NULL
                    GROUP BY p.predicted_outcome
                ''')
                
                outcome_stats = []
                for row in cursor.fetchall():
                    outcome_accuracy = (row[2] / row[1] * 100) if row[1] > 0 else 0
                    outcome_stats.append({
                        'predicted_outcome': row[0],
                        'total_predictions': row[1],
                        'correct_predictions': row[2],
                        'accuracy': round(outcome_accuracy, 1)
                    })
                
                return {
                    'overall': {
                        'total_predictions': total_predictions,
                        'correct_predictions': correct_predictions,
                        'accuracy': round(overall_accuracy, 1)
                    },
                    'by_confidence': confidence_stats,
                    'by_outcome': outcome_stats
                }
                
        except Exception as e:
            print(f"Error getting prediction statistics: {e}")
            return {
                'overall': {'total_predictions': 0, 'correct_predictions': 0, 'accuracy': 0},
                'by_confidence': [],
                'by_outcome': []
            }
    
    def update_accuracy_tracking(self):
        """Update the accuracy tracking table with latest comparisons."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clear existing accuracy records
                cursor.execute('DELETE FROM prediction_accuracy')
                
                # Insert new accuracy records
                cursor.execute('''
                    INSERT INTO prediction_accuracy (
                        prediction_id, match_id, was_correct, confidence_bucket, prediction_method
                    )
                    SELECT 
                        p.id,
                        p.match_id,
                        (p.predicted_outcome = r.actual_outcome) as was_correct,
                        CASE 
                            WHEN p.confidence >= 80 THEN 'ELITE'
                            WHEN p.confidence >= 70 THEN 'HIGH'
                            WHEN p.confidence >= 50 THEN 'MEDIUM'
                            ELSE 'LOW'
                        END as confidence_bucket,
                        p.prediction_method
                    FROM predictions p
                    JOIN match_results r ON p.match_id = r.match_id
                    WHERE r.actual_outcome IS NOT NULL
                ''')
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating accuracy tracking: {e}")
            return False
    
    def save_prediction_batch(self, batch_name: str, predictions_data: List[Dict]) -> Optional[int]:
        """Save a batch of predictions with a custom name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create batch record
                cursor.execute('''
                    INSERT INTO prediction_batches (batch_name, batch_date, description, total_predictions)
                    VALUES (?, ?, ?, ?)
                ''', (
                    batch_name,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    f"Manual prediction batch: {batch_name}",
                    len(predictions_data)
                ))
                
                batch_id = cursor.lastrowid
                
                # Save predictions with batch association
                for match_data, prediction_data in predictions_data:
                    self.save_prediction_with_batch(match_data, prediction_data, batch_id, conn)
                
                conn.commit()
                return batch_id
                
        except Exception as e:
            print(f"Error saving prediction batch: {e}")
            return None
    
    def save_prediction_with_batch(self, match_data: Dict, prediction_data: Dict, batch_id: int, conn=None) -> bool:
        """Save a prediction with batch association."""
        try:
            if conn is None:
                conn = sqlite3.connect(self.db_path)
                should_close = True
            else:
                should_close = False
                
            cursor = conn.cursor()
            
            # Extract match information
            match_id = match_data.get('id')
            home_team = match_data.get('homeTeam', {})
            away_team = match_data.get('awayTeam', {})
            competition = match_data.get('competition', {})
            
            # Prepare team stats as JSON
            team_stats_json = json.dumps(prediction_data.get('team_stats', {}))
            
            cursor.execute('''
                INSERT OR REPLACE INTO predictions (
                    match_id, home_team_id, away_team_id, home_team_name, away_team_name,
                    competition_id, competition_name, match_date, predicted_outcome,
                    predicted_team, confidence, home_win_prob, draw_prob, away_win_prob,
                    ht_home_win_ft_lose_prob, ht_away_win_ft_lose_prob, reasoning, team_stats, batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_id,
                home_team.get('id'),
                away_team.get('id'),
                home_team.get('name', 'Unknown'),
                away_team.get('name', 'Unknown'),
                competition.get('id'),
                competition.get('name', 'Unknown'),
                match_data.get('utcDate'),
                prediction_data.get('prediction'),
                prediction_data.get('predicted_team'),
                prediction_data.get('confidence'),
                prediction_data.get('probabilities', {}).get('home_win'),
                prediction_data.get('probabilities', {}).get('draw'),
                prediction_data.get('probabilities', {}).get('away_win'),
                prediction_data.get('probabilities', {}).get('ht_home_win_ft_lose'),
                prediction_data.get('probabilities', {}).get('ht_away_win_ft_lose'),
                prediction_data.get('reasoning'),
                team_stats_json,
                batch_id
            ))
            
            if should_close:
                conn.commit()
                conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error saving prediction with batch: {e}")
            return False
    
    def get_prediction_batches(self) -> List[Dict]:
        """Get all saved prediction batches."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, batch_name, batch_date, description, total_predictions, created_at
                    FROM prediction_batches
                    ORDER BY created_at DESC
                ''')
                
                rows = cursor.fetchall()
                batches = []
                
                for row in rows:
                    batches.append({
                        'id': row[0],
                        'batch_name': row[1],
                        'batch_date': row[2],
                        'description': row[3],
                        'total_predictions': row[4],
                        'created_at': row[5]
                    })
                
                return batches
                
        except Exception as e:
            print(f"Error getting prediction batches: {e}")
            return []
    
    def get_batch_predictions(self, batch_id: int) -> List[Dict]:
        """Get predictions for a specific batch."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        p.match_id, p.home_team_name, p.away_team_name,
                        p.competition_name, p.match_date, p.predicted_outcome,
                        p.predicted_team, p.confidence, p.home_win_prob,
                        p.draw_prob, p.away_win_prob, p.reasoning
                    FROM predictions p
                    WHERE p.batch_id = ?
                    ORDER BY p.match_date ASC
                ''', (batch_id,))
                
                rows = cursor.fetchall()
                predictions = []
                
                for row in rows:
                    predictions.append({
                        'match_id': row[0],
                        'home_team': row[1],
                        'away_team': row[2],
                        'competition': row[3],
                        'match_date': row[4],
                        'predicted_outcome': row[5],
                        'predicted_team': row[6],
                        'confidence': row[7],
                        'probabilities': {
                            'home_win': row[8],
                            'draw': row[9],
                            'away_win': row[10]
                        },
                        'reasoning': row[11]
                    })
                
                return predictions
                
        except Exception as e:
            print(f"Error getting batch predictions: {e}")
            return []
    
    def get_batch_comparison(self, batch_id: int) -> Dict:
        """Get comparison between batch predictions and actual results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get batch predictions with results
                cursor.execute('''
                    SELECT 
                        p.match_id, p.home_team_name, p.away_team_name,
                        p.competition_name, p.match_date, p.predicted_outcome,
                        p.predicted_team, p.confidence, p.home_win_prob,
                        p.draw_prob, p.away_win_prob, p.reasoning,
                        r.home_score, r.away_score, r.actual_outcome
                    FROM predictions p
                    LEFT JOIN match_results r ON p.match_id = r.match_id
                    WHERE p.batch_id = ?
                    ORDER BY p.match_date ASC
                ''', (batch_id,))
                
                rows = cursor.fetchall()
                comparisons = []
                total_predictions = len(rows)
                correct_predictions = 0
                finished_matches = 0
                
                for row in rows:
                    match_id = row[0]
                    predicted_outcome = row[5]
                    actual_outcome = row[14]
                    
                    is_correct = None
                    if actual_outcome:
                        finished_matches += 1
                        is_correct = predicted_outcome == actual_outcome
                        if is_correct:
                            correct_predictions += 1
                    
                    comparisons.append({
                        'match_id': match_id,
                        'home_team': row[1],
                        'away_team': row[2],
                        'competition': row[3],
                        'match_date': row[4],
                        'prediction': {
                            'predicted_outcome': predicted_outcome,
                            'predicted_team': row[6],
                            'confidence': row[7],
                            'probabilities': {
                                'home_win': row[8],
                                'draw': row[9],
                                'away_win': row[10]
                            },
                            'reasoning': row[11]
                        },
                        'result': {
                            'home_score': row[12],
                            'away_score': row[13],
                            'actual_outcome': actual_outcome
                        } if actual_outcome else None,
                        'was_correct': is_correct
                    })
                
                # Calculate win ratio
                win_ratio = (correct_predictions / finished_matches * 100) if finished_matches > 0 else 0
                
                return {
                    'comparisons': comparisons,
                    'statistics': {
                        'total_predictions': total_predictions,
                        'finished_matches': finished_matches,
                        'correct_predictions': correct_predictions,
                        'win_ratio': round(win_ratio, 1)
                    }
                }
                
        except Exception as e:
            print(f"Error getting batch comparison: {e}")
            return {'comparisons': [], 'statistics': {'total_predictions': 0, 'finished_matches': 0, 'correct_predictions': 0, 'win_ratio': 0}}
    
    def delete_prediction_batch(self, batch_id: int) -> bool:
        """Delete a prediction batch and all its associated predictions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, delete all predictions associated with this batch
                cursor.execute('DELETE FROM predictions WHERE batch_id = ?', (batch_id,))
                
                # Then, delete the batch record itself
                cursor.execute('DELETE FROM prediction_batches WHERE id = ?', (batch_id,))
                
                # Also clean up any accuracy records that might be orphaned
                cursor.execute('''
                    DELETE FROM prediction_accuracy 
                    WHERE prediction_id NOT IN (SELECT id FROM predictions)
                ''')
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error deleting prediction batch: {e}")
            return False
    
