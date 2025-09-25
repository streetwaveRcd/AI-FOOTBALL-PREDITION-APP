import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

class UserDatabase:
    """Database handler for user authentication and IP tracking."""
    
    def __init__(self, db_path: str = 'user_data.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Create IP tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    request_count INTEGER DEFAULT 0,
                    last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ip_address)
                )
            ''')
            
            # Create user sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def register_user(self, username: str) -> Optional[int]:
        """Register a new user with username only."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (username) VALUES (?)
                ''', (username,))
                
                user_id = cursor.lastrowid
                conn.commit()
                return user_id
                
        except sqlite3.IntegrityError:
            # Username already exists
            return None
        except Exception as e:
            print(f"Error registering user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, created_at, last_login, is_active
                    FROM users WHERE username = ? AND is_active = TRUE
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'created_at': row[2],
                        'last_login': row[3],
                        'is_active': bool(row[4])
                    }
                return None
                
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
    
    def update_user_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating user login: {e}")
            return False
    
    def create_user_session(self, user_id: int, session_id: str, ip_address: str) -> bool:
        """Create a new user session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Deactivate any existing sessions for this user
                cursor.execute('''
                    UPDATE user_sessions SET is_active = FALSE WHERE user_id = ?
                ''', (user_id,))
                
                # Create new session
                cursor.execute('''
                    INSERT INTO user_sessions (session_id, user_id, ip_address)
                    VALUES (?, ?, ?)
                ''', (session_id, user_id, ip_address))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error creating user session: {e}")
            return False
    
    def get_user_by_session(self, session_id: str) -> Optional[Dict]:
        """Get user by session ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.id, u.username, u.created_at, u.last_login, s.ip_address
                    FROM users u
                    JOIN user_sessions s ON u.id = s.user_id
                    WHERE s.session_id = ? AND s.is_active = TRUE AND u.is_active = TRUE
                ''', (session_id,))
                
                row = cursor.fetchone()
                if row:
                    # Update session last accessed time
                    cursor.execute('''
                        UPDATE user_sessions SET last_accessed = CURRENT_TIMESTAMP
                        WHERE session_id = ?
                    ''', (session_id,))
                    conn.commit()
                    
                    return {
                        'id': row[0],
                        'username': row[1],
                        'created_at': row[2],
                        'last_login': row[3],
                        'session_ip': row[4]
                    }
                return None
                
        except Exception as e:
            print(f"Error getting user by session: {e}")
            return None
    
    def logout_user(self, session_id: str) -> bool:
        """Logout user by deactivating session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE user_sessions SET is_active = FALSE WHERE session_id = ?
                ''', (session_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error logging out user: {e}")
            return False
    
    def track_ip_request(self, ip_address: str) -> Dict[str, any]:
        """Track IP request and return usage info."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if IP exists
                cursor.execute('''
                    SELECT id, request_count, last_request, date_reset
                    FROM ip_tracking WHERE ip_address = ?
                ''', (ip_address,))
                
                row = cursor.fetchone()
                current_time = datetime.now()
                
                if row:
                    # Check if we need to reset the counter (daily reset)
                    last_reset = datetime.fromisoformat(row[3])
                    if (current_time - last_reset).days >= 1:
                        # Reset counter for new day
                        cursor.execute('''
                            UPDATE ip_tracking 
                            SET request_count = 1, last_request = ?, date_reset = ?
                            WHERE ip_address = ?
                        ''', (current_time, current_time, ip_address))
                        request_count = 1
                    else:
                        # Increment counter
                        new_count = row[1] + 1
                        cursor.execute('''
                            UPDATE ip_tracking 
                            SET request_count = ?, last_request = ?
                            WHERE ip_address = ?
                        ''', (new_count, current_time, ip_address))
                        request_count = new_count
                else:
                    # New IP address
                    cursor.execute('''
                        INSERT INTO ip_tracking (ip_address, request_count, last_request, date_reset)
                        VALUES (?, 1, ?, ?)
                    ''', (ip_address, current_time, current_time))
                    request_count = 1
                
                conn.commit()
                
                return {
                    'request_count': request_count,
                    'limit_exceeded': request_count > 5,
                    'remaining_requests': max(0, 5 - request_count)
                }
                
        except Exception as e:
            print(f"Error tracking IP request: {e}")
            return {
                'request_count': 0,
                'limit_exceeded': False,
                'remaining_requests': 5
            }
    
    def get_ip_usage(self, ip_address: str) -> Dict[str, any]:
        """Get current IP usage without incrementing counter."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT request_count, last_request, date_reset
                    FROM ip_tracking WHERE ip_address = ?
                ''', (ip_address,))
                
                row = cursor.fetchone()
                if row:
                    current_time = datetime.now()
                    last_reset = datetime.fromisoformat(row[2])
                    
                    # Check if counter should be reset
                    if (current_time - last_reset).days >= 1:
                        request_count = 0
                    else:
                        request_count = row[0]
                    
                    return {
                        'request_count': request_count,
                        'limit_exceeded': request_count >= 5,
                        'remaining_requests': max(0, 5 - request_count)
                    }
                else:
                    return {
                        'request_count': 0,
                        'limit_exceeded': False,
                        'remaining_requests': 5
                    }
                
        except Exception as e:
            print(f"Error getting IP usage: {e}")
            return {
                'request_count': 0,
                'limit_exceeded': False,
                'remaining_requests': 5
            }
    
    def get_user_stats(self) -> Dict:
        """Get user registration statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_users,
                        COUNT(CASE WHEN last_login IS NOT NULL THEN 1 END) as users_with_logins
                    FROM users
                ''')
                
                row = cursor.fetchone()
                if row:
                    return {
                        'total_users': row[0],
                        'active_users': row[1],
                        'users_with_logins': row[2]
                    }
                
                return {
                    'total_users': 0,
                    'active_users': 0,
                    'users_with_logins': 0
                }
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'users_with_logins': 0
            }
    
    def cleanup_old_sessions(self, days: int = 30) -> bool:
        """Clean up old inactive sessions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE last_accessed < datetime('now', '-{} days')
                    AND is_active = FALSE
                '''.format(days))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error cleaning up old sessions: {e}")
            return False